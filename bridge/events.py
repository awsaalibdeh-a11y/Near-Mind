"""The validated inbound boundary.

A real neighbour's reply is unpredictable: emoji, Arabic, a five-paragraph
voice-note transcript, an empty body, JSON that looks like our own protocol,
a `null` sender, a 10 MB string, a control character. **Every** inbound message
becomes an :class:`InboundEvent` *before* it can touch agent state, and the
validation is total: :func:`validate_inbound` returns either a valid event or a
:class:`ValidationFailure`, never an exception and never a half-built object.

The backend contract is deliberately dumb and safe:

* a validated event carries a **kind** from a closed set and a **body** that is
  already normalised (trimmed, length-capped, control chars stripped);
* anything that fails validation is surfaced as a ``ValidationFailure`` with a
  stable ``reason`` code — the caller logs it as a decision and moves on;
* the ledger, inventory and dashboard only ever see ``InboundEvent`` objects,
  so a malformed reply structurally cannot reach them as a "reply".

Phone numbers never appear here. Identities are opaque :class:`ContactRef`
values resolved by the bridge away from the wire.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional

from .commands import CommandKind, ParsedCommand, parse_command

#: Hard caps. WhatsApp itself caps a text body at ~65 536 UTF-16 units; we cap
#: far lower because a neighbour reply that is 4 000 chars is not a reply, it
#: is something else. The backend must never hold unbounded input.
MAX_BODY_CHARS = 4_000
MAX_MEDIA_LABEL_CHARS = 64
MAX_SENDER_ID_CHARS = 200
MAX_MESSAGE_ID_CHARS = 200
MAX_RAW_CHARS = 1_000_000  # refuse to even normalise beyond this

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")


class InboundKind(str, Enum):
    """What the inbound message *is*, from the bridge's point of view."""

    COMMAND = "command"      # STOP / BUSY / RESUME / HELP — control plane
    TEXT = "text"            # a free-text human reply
    MEDIA = "media"          # a reply carrying a file (photo, voice note)
    UNKNOWN = "unknown"      # valid envelope, unclassifiable content
    REACTION = "reaction"    # emoji reaction, no body — ignored by agent flow


@dataclass(frozen=True)
class ContactRef:
    """An opaque, resolved neighbour identity — never a raw phone number.

    The bridge maps a WhatsApp JID to a ``ContactRef`` via a local contact map;
    the number itself stays in the transport layer and out of the domain model
    (and out of logs, dashboards and exports).
    """

    contact_id: str
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.contact_id, str) or not self.contact_id:
            raise ValueError("contact_id must be a non-empty string")
        # contact_id is an internal key, not a phone number — but guard anyway.
        if any(ch.isdigit() for ch in self.contact_id) and len(self.contact_id) > 14:
            raise ValueError("contact_id looks like a phone number; use an opaque id")


@dataclass(frozen=True)
class InboundEvent:
    """A schema-valid inbound message. The only shape agent state accepts."""

    kind: InboundKind
    sender: ContactRef
    received_at: datetime
    message_id: str
    body: str = ""
    media_label: Optional[str] = None
    command: Optional[ParsedCommand] = None
    #: Whether the bridge *itself* is the recipient (always true on this
    #: transport) — kept so the identity model is explicit, not implied.
    addressed_to_bridge: bool = True
    #: Free-form hints (e.g. ``is_group``) — never trusted by business logic.
    hints: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind is InboundKind.COMMAND and self.command is None:
            raise ValueError("a COMMAND event requires a parsed command")
        if self.command is not None and self.kind is not InboundKind.COMMAND:
            raise ValueError("only COMMAND events carry a parsed command")
        if not self.message_id:
            raise ValueError("message_id is required")

    @property
    def is_control_command(self) -> bool:
        return self.kind is InboundKind.COMMAND

    @property
    def command_kind(self) -> Optional[CommandKind]:
        return self.command.kind if self.command else None


@dataclass(frozen=True)
class ValidationFailure:
    """Returned instead of an :class:`InboundEvent` when input is bad.

    ``reason`` is a stable slug the backend can switch on; ``detail`` is
    human-readable and safe to put in a decision log (it contains no phone
    numbers — it is derived only from structure, never from the raw payload).
    """

    reason: str
    detail: str
    #: A stable hash-safe fingerprint of where it came from, if known.
    sender_hint: Optional[str] = None

    @property
    def is_failure(self) -> bool:
        return True


#: The closed set of failure slugs. Adding one is a deliberate contract change.
FAILURE_REASONS = frozenset(
    {
        "empty_body",
        "not_mapping",
        "missing_sender",
        "missing_message_id",
        "from_self",
        "group_chat",
        "too_large",
        "unsupported_type",
        "bad_timestamp",
    }
)


def _strip_invisible(text: str) -> str:
    text = _ZERO_WIDTH.sub("", text)
    text = _CONTROL_CHARS.sub("", text)
    return text


def _normalise_body(text: Any) -> tuple[str, bool]:
    """Return (normalised_body, too_large)."""
    if text is None:
        return "", False
    if not isinstance(text, str):
        # Some transports hand back numbers / lists. Coerce safely.
        try:
            text = str(text)
        except Exception:
            return "", False
    if len(text) > MAX_RAW_CHARS:
        return "", True
    text = _strip_invisible(text)
    text = text.strip()
    if len(text) > MAX_BODY_CHARS:
        # Keep a bounded prefix but flag truncation in-page (caller cannot
        # distinguish, so we mark it in the body with an ellipsis).
        text = text[:MAX_BODY_CHARS].rstrip() + "\u2026"
    return text, False


def _parse_ts(value: Any) -> Optional[datetime]:
    """Best-effort RFC 3339 / epoch parse. Returns aware UTC or None."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Epoch seconds (WhatsApp) — reject implausible values.
        try:
            if value > 1e12:  # ms
                value = value / 1000.0
            if 0 < value < 4_102_444_800:  # before year 2100
                return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return None
    if isinstance(value, str) and value.strip():
        raw = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def classify_body(body: str, media_label: Optional[str]) -> tuple[InboundKind, Optional[ParsedCommand]]:
    """Decide what a normalised body is.

    Order matters: a command wins over text, because ``STOP`` is a control
    plane and must never be mistaken for a neighbour reply ("got it, stop
    by anytime" is falsed-out by the exact-phrase/word rule in the parser).
    """
    command = parse_command(body) if body else None
    if command is not None:
        return InboundKind.COMMAND, command
    if body:
        # Text wins over media: a photo with a caption is answered as text,
        # with the label kept as an attribute of the reply.
        return InboundKind.TEXT, None
    if media_label:
        return InboundKind.MEDIA, None
    return InboundKind.UNKNOWN, None


def validate_inbound(
    payload: Any,
    *,
    contact_index: Mapping[str, ContactRef],
    now: Optional[datetime] = None,
    max_age_seconds: Optional[int] = None,
) -> InboundEvent | ValidationFailure:
    """Validate one raw inbound message from the transport.

    ``payload`` is whatever the transport (MCP ``list_messages``) hands back —
    a dict-shaped message. ``contact_index`` maps the transport's opaque sender
    key (a JID) to a resolved :class:`ContactRef`; the bridge owns that map and
    is the only place it is built.

    Never raises. Returns an event or a :class:`ValidationFailure`.
    """
    now = now or datetime.now(timezone.utc)

    if not isinstance(payload, Mapping):
        return ValidationFailure("not_mapping", "inbound payload was not a mapping")

    # --- sender -----------------------------------------------------------
    raw_sender = payload.get("sender") or payload.get("from")
    if not isinstance(raw_sender, str) or not raw_sender.strip():
        return ValidationFailure("missing_sender", "inbound had no sender")
    raw_sender = raw_sender.strip()
    if len(raw_sender) > MAX_SENDER_ID_CHARS:
        return ValidationFailure("missing_sender", "sender key was implausibly long")

    if payload.get("is_from_me") is True:
        return ValidationFailure("from_self", "ignored a message sent by the linked account itself")
    if raw_sender.endswith("@g.us") or payload.get("is_group") is True:
        # The bridge is a 1:1 private channel to real neighbours. Group traffic
        # is out of scope and must never be mined for STATE / commands.
        return ValidationFailure("group_chat", "ignored a group-chat message")

    sender = contact_index.get(raw_sender)
    if sender is None:
        # An unknown sender is still a *valid* envelope — we just cannot map it.
        # Surfacing this as failure is the safe choice: an unknown number must
        # never be able to issue STOP for someone else.
        return ValidationFailure(
            "missing_sender",
            "sender is not a known neighbour; refusing to attribute the message",
            sender_hint="unmapped",
        )

    # --- message id -------------------------------------------------------
    raw_id = payload.get("id") or payload.get("message_id")
    if not isinstance(raw_id, str) or not raw_id.strip():
        return ValidationFailure("missing_message_id", "inbound had no message id", sender.contact_id)
    raw_id = raw_id.strip()
    if len(raw_id) > MAX_MESSAGE_ID_CHARS:
        raw_id = raw_id[:MAX_MESSAGE_ID_CHARS]

    # --- timestamp --------------------------------------------------------
    ts = _parse_ts(payload.get("timestamp") or payload.get("time") or payload.get("t"))
    if ts is None:
        return ValidationFailure(
            "bad_timestamp",
            "inbound timestamp could not be parsed; refusing to order it",
            sender.contact_id,
        )
    age = (now - ts).total_seconds()
    if max_age_seconds is not None and age > max_age_seconds:
        # A stale message (old backlog on first connect) must not be replayed
        # as a live reply — it could re-trigger a STOP that was already lifted.
        return ValidationFailure(
            "unsupported_type",
            "inbound was older than the replay window; not treated as a live event",
            sender.contact_id,
        )
    if age < -300:
        # More than 5 minutes in the future: suspect clock skew; still accept
        # but clamp so ordering stays monotonic-ish (done by caller).
        pass

    # --- content ----------------------------------------------------------
    media_label = payload.get("media_type") or payload.get("type")
    if isinstance(media_label, str):
        media_label = _strip_invisible(media_label).strip().lower()[:MAX_MEDIA_LABEL_CHARS]
    else:
        media_label = None
    # A "type" of "text" is not media; only real media types count.
    if media_label in ("text", "chat", "conversation", ""):
        media_label = None

    body, too_large = _normalise_body(payload.get("content") or payload.get("body") or payload.get("text"))
    if too_large:
        return ValidationFailure("too_large", "inbound body exceeded the hard size limit", sender.contact_id)

    # Reactions carry no body and no media — ignore, do not treat as a reply.
    if payload.get("is_reaction") is True or (
        media_label and media_label.startswith("reaction")
    ):
        return InboundEvent(
            kind=InboundKind.REACTION,
            sender=sender,
            received_at=ts,
            message_id=raw_id,
            body="",
            media_label=None,
            hints={"is_group": False},
        )

    kind, command = classify_body(body, media_label)

    return InboundEvent(
        kind=kind,
        sender=sender,
        received_at=ts,
        message_id=raw_id,
        body=body,
        media_label=media_label,
        command=command,
        hints={"is_group": False},
    )


# ---------------------------------------------------------------------------
# Outbound results — symmetric, typed shapes the backend switches on.
# ---------------------------------------------------------------------------


class SendOutcome(str, Enum):
    SENT = "sent"                # transport confirmed delivery to WhatsApp
    REFUSED = "refused"          # the bridge declined to send (rule, not error)
    FAILED = "failed"            # transport error, retryable or not
    SUPPRESSED = "suppressed"    # recipient said STOP (or is out of building)


@dataclass(frozen=True)
class OutboundReceipt:
    """A record of one attempted outbound message."""

    outcome: SendOutcome
    contact: ContactRef
    sent_at: datetime
    message_id: Optional[str] = None
    reason: Optional[str] = None   # stable slug for REFUSED / SUPPRESSED
    detail: Optional[str] = None   # human-readable, safe for logs
    #: How many messages to this contact this rolling day *after* this one.
    daily_count: int = 0

    @property
    def delivered(self) -> bool:
        return self.outcome is SendOutcome.SENT


@dataclass(frozen=True)
class OutboundResult:
    """One send request, possibly spanning multiple messages.

    ``receipts`` is ordered; ``primary`` is the first one. A multi-part send
    that half-succeeds is reported as ``partial`` so the backend can decide.
    """

    receipts: tuple[OutboundReceipt, ...]

    @property
    def primary(self) -> OutboundReceipt:
        return self.receipts[0]

    @property
    def delivered(self) -> bool:
        return any(r.outcome is SendOutcome.SENT for r in self.receipts)

    @property
    def partial(self) -> bool:
        outcomes = {r.outcome for r in self.receipts}
        return SendOutcome.SENT in outcomes and len(outcomes) > 1
