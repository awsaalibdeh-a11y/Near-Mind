"""The bridge facade — the interface the Flask backend calls.

Four verbs, exactly as the issue asks:

    resolve_contact(contact_id) -> ResolvedContact | None
    send(contact_id, body)      -> OutboundReceipt
    receive(now=None)           -> list[InboundEvent | ValidationFailure]
    report()                    -> BridgeStatus  (delivery + guardrail state)

plus ``availability`` / ``limiter`` accessors for the dashboard and inspector.

Order of checks on **every** outbound (this ordering is the product):

1. Resolve the contact. Unknown -> REFUSED (never guess a recipient).
2. ``STOP`` in force -> SUPPRESSED. This check is *before* the limiter and
   catches every message type, so a stopped person is never messaged again —
   full stop, not "unless it was important".
3. Not at home / out -> SUPPRESSED.
4. Busy -> SUPPRESSED for non-urgent; the *caller* passes ``urgent=True`` for
   an emergency, and even then the reason says so.
5. Control acknowledgement (the one message owed after STOP/BUSY) -> exempt
   from the limiter, but still counted. This is the only exemption.
6. Rate limiter -> REFUSED with a retry hint.
7. Transport send. Success -> SENT; error -> FAILED (retryable per receipt).

Inbound is the reverse: transport poll -> validate (total, never raises) ->
dedupe -> apply command to availability -> hand the customer a typed event.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping, Optional

from .availability import Availability, AvailabilityState, AvailabilityStore, Transition
from .commands import CommandKind, ParsedCommand
from .config import BridgeConfig
from .events import (
    ContactRef,
    InboundEvent,
    InboundKind,
    OutboundReceipt,
    SendOutcome,
    ValidationFailure,
    validate_inbound,
)
from .limiter import RateDecision, RateLimiter
from .transport import FakeTransport, TransportError, WhatsAppTransport

log = logging.getLogger("bridge")

#: What to say when we acknowledge a control command. Server-side display text,
#: kept here so the product voice is reviewable in one place. No emoji — the
#: tone is "utility", not "brand".
ACK_TEXT = {
    CommandKind.STOP: (
        "Done — you've been set to STOP. NearMind won't message you again "
        "until you send RESUME."
    ),
    CommandKind.BUSY: (
        "Got it — marked BUSY for {duration}. I'll leave you alone until then "
        "(send RESUME to come back early)."
    ),
    CommandKind.RESUME: "Thanks — you're available again.",
    CommandKind.HELP: (
        "NearMind commands: STOP (never message me until I say RESUME), "
        "BUSY (busy for an hour; add a time like BUSY 30M), RESUME (I'm back)."
    ),
}


@dataclass(frozen=True)
class ResolvedContact:
    contact_id: str
    display_name: str
    #: True if a real wire recipient exists. False = simulated identity that
    #: only exists in the sandbox, so a send must fail closed.
    has_real_wire: bool
    availability: Availability


@dataclass(frozen=True)
class InboundBatch:
    """Result of one poll cycle. Both lists are always present."""

    events: tuple[InboundEvent, ...] = ()
    failures: tuple[ValidationFailure, ...] = ()
    #: Availability transitions caused by control commands this cycle.
    transitions: tuple[tuple[str, Transition], ...] = ()
    #: Window start used for the poll (None = first poll).
    polled_since: Optional[datetime] = None

    @property
    def empty(self) -> bool:
        return not self.events and not self.failures


@dataclass(frozen=True)
class BridgeStatus:
    """Everything the dashboard needs to tell the truth about the bridge."""

    mode: str                 # "dry_run" | "live"
    transport: str            # "fake" | "mcp_stdio"
    linked_identity: str
    sandbox: bool
    sent_total: int
    suppressed_total: int
    refused_total: int
    failed_total: int
    inbound_total: int
    invalid_inbound_total: int
    #: per-contact guardrail snapshot
    guards: Mapping[str, dict] = field(default_factory=dict)
    last_poll_at: Optional[datetime] = None

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "transport": self.transport,
            "linked_identity": self.linked_identity,
            "sandbox": self.sandbox,
            "counters": {
                "sent": self.sent_total,
                "suppressed": self.suppressed_total,
                "refused": self.refused_total,
                "failed": self.failed_total,
                "inbound": self.inbound_total,
                "invalid_inbound": self.invalid_inbound_total,
            },
            "guards": dict(self.guards),
            "last_poll_at": self.last_poll_at.isoformat() if self.last_poll_at else None,
        }


class WhatsAppBridge:
    """The bridge. One linked account; many simulated or real identities.

    Construction is side-effect free apart from opening the transport. In
    dry-run (the default) the transport is forced to :class:`FakeTransport`,
    so an accidental call can never reach a real number.
    """

    def __init__(
        self,
        *,
        config: Optional[BridgeConfig] = None,
        transport: Optional[WhatsAppTransport] = None,
        contacts: Optional[Mapping[str, str]] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.config = config or BridgeConfig()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._contacts: dict[str, ContactRef] = dict(contacts or {})  # type: ignore[assignment]

        dry = self.config.effective_dry_run()
        if dry:
            if transport is not None and not getattr(transport, "is_fake", False):
                log.warning(
                    "bridge is in dry-run; ignoring a non-fake transport and using "
                    "the in-memory fake so no real send is possible"
                )
            wire = {cid: f"fake-{cid}" for cid in self._contacts}
            self.transport: WhatsAppTransport = transport if getattr(
                transport, "is_fake", False
            ) else FakeTransport(wire, clock=self._clock)
            self._mode = "dry_run"
        else:
            if transport is None:
                raise ValueError(
                    "live mode requires an explicit transport (McpStdioTransport)"
                )
            self.transport = transport
            self._mode = "live"

        self.availability = AvailabilityStore(
            default_busy_seconds=self.config.availability.default_busy_seconds,
            max_busy_seconds=self.config.availability.max_busy_seconds,
            clock=self._clock,
        )
        self.limiter = RateLimiter(self.config.rate_limits, clock=self._clock)

        self._contact_index: dict[str, ContactRef] = {}
        for cid, ref in self._contacts.items():
            key = self.transport.resolve_key(cid)
            if key:
                self._contact_index[key] = ref

        self._seen_ids: set[str] = set()
        self._last_poll_at: Optional[datetime] = None
        self._started_at = self._clock()

        self._sent = 0
        self._suppressed = 0
        self._refused = 0
        self._failed = 0
        self._inbound = 0
        self._invalid = 0

    # -- introspection ---------------------------------------------------

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_fake_transport(self) -> bool:
        return bool(getattr(self.transport, "is_fake", False))

    def close(self) -> None:
        try:
            self.transport.close()
        except Exception:  # pragma: no cover - best effort
            pass

    # -- 1. resolve ------------------------------------------------------

    def resolve_contact(
        self, contact_id: str, *, now: Optional[datetime] = None
    ) -> Optional[ResolvedContact]:
        ref = self._contacts.get(contact_id)
        if ref is None:
            return None
        return ResolvedContact(
            contact_id=ref.contact_id,
            display_name=ref.display_name,
            has_real_wire=self.transport.resolve_key(contact_id) is not None,
            availability=self.availability.ensure(contact_id, now),
        )

    def register_contact(self, ref: ContactRef, wire_key: Optional[str]) -> None:
        """Add a neighbour at runtime (config load). ``wire_key`` is the JID."""
        self._contacts[ref.contact_id] = ref
        if wire_key:
            self._contact_index[wire_key] = ref

    # -- 2. send ---------------------------------------------------------

    def send(
        self,
        contact_id: str,
        body: str,
        *,
        urgent: bool = False,
        acknowledge: Optional[CommandKind] = None,
        now: Optional[datetime] = None,
    ) -> OutboundReceipt:
        """Send one message. Total: returns a receipt, never raises for a
        refusal. A transport exception becomes a FAILED receipt.
        """
        now = self._now(now)
        ref = self._contacts.get(contact_id)
        if ref is None:
            self._refused += 1
            return OutboundReceipt(
                SendOutcome.REFUSED,
                ContactRef(contact_id, contact_id),
                now,
                reason="unknown_contact",
                detail=f"no neighbour with id {contact_id!r}; refusing to guess a recipient",
            )

        av = self.availability.ensure(contact_id, now)

        # 2. STOP is absolute. No urgent override. Ever. The *only* message a
        #    stopped person may receive is the acknowledgement of the STOP
        #    itself (and of a BUSY that arrived before it) — otherwise they
        #    would never learn the command landed. This is a one-message
        #    carve-out, not an opening for agent chatter.
        ack_owed_while_stopped = acknowledge in (
            CommandKind.STOP,
            CommandKind.BUSY,
        )
        if av.is_stopped and not ack_owed_while_stopped:
            self._suppressed += 1
            return OutboundReceipt(
                SendOutcome.SUPPRESSED,
                ref,
                now,
                reason="stopped",
                detail=f"{ref.display_name} sent STOP — not messaged again until they resume",
            )

        # 3. Out of the building: not reachable, not even softly. A command
        #    acknowledgement still goes out — they took an action and one
        #    "done, noted" is owed, even when the action was "go away".
        if av.state is AvailabilityState.NOT_AT_HOME and not ack_owed_while_stopped:
            self._suppressed += 1
            return OutboundReceipt(
                SendOutcome.SUPPRESSED,
                ref,
                now,
                reason="not_at_home",
                detail=f"{ref.display_name} is not at home ({av.reason})",
            )

        # 4. Busy: route around, unless the caller declares an emergency.
        if av.state is AvailabilityState.BUSY and not urgent and acknowledge is None:
            self._suppressed += 1
            return OutboundReceipt(
                SendOutcome.SUPPRESSED,
                ref,
                now,
                reason="busy",
                detail=f"{ref.display_name} is busy ({av.reason}); not barging in",
            )

        wire = self.transport.resolve_key(contact_id)
        if wire is None:
            # Simulated identity with no real number — fail closed.
            self._suppressed += 1
            return OutboundReceipt(
                SendOutcome.SUPPRESSED,
                ref,
                now,
                reason="simulated_identity",
                detail=(
                    f"{ref.display_name} is a simulated identity; there is no real "
                    "WhatsApp number to send to"
                ),
            )

        text = body
        if acknowledge is not None:
            text = _render_ack(acknowledge, av)

        # 5/6. Rate limit — exempt only a command acknowledgement.
        decision: RateDecision
        if acknowledge is not None:
            decision = RateDecision(True, None, detail="control acknowledgement exempt")
            self.limiter.register_outbound(contact_id, text, now=now)
        else:
            decision = self.limiter.check_and_consume(contact_id, text, now=now)
            if decision.denied:
                self._refused += 1
                return OutboundReceipt(
                    SendOutcome.REFUSED,
                    ref,
                    now,
                    reason=decision.refusal.value if decision.refusal else "rate_limited",
                    detail=decision.detail,
                    daily_count=decision.daily_used,
                )

        # 7. Transport.
        try:
            mid = self.transport.send_text(wire, text)
        except TransportError as exc:
            self._failed += 1
            return OutboundReceipt(
                SendOutcome.FAILED,
                ref,
                now,
                reason="transport_error",
                detail=str(exc),
                daily_count=decision.daily_used,
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._failed += 1
            return OutboundReceipt(
                SendOutcome.FAILED,
                ref,
                now,
                reason="transport_exception",
                detail=f"{type(exc).__name__}",
            )

        if acknowledge is None:
            self.limiter.mark_unanswered(contact_id)
        self._sent += 1
        return OutboundReceipt(
            SendOutcome.SENT,
            ref,
            now,
            message_id=mid,
            detail="delivered to transport",
            daily_count=decision.daily_used,
        )

    def may_contact(
        self, contact_id: str, *, now: Optional[datetime] = None, asleep: bool = False
    ) -> tuple[bool, str]:
        """Pre-flight for the agent's eligibility filter: availability + guards.

        This is the *cheapest* combined answer and the one the backend should
        log in a decision reason when it skips outreach.
        """
        allowed, reason = self.availability.may_contact(
            contact_id, now=now, asleep=asleep
        )
        if not allowed:
            return False, reason
        # Probe the volume/burst/silence guards without a duplicate probe: a
        # blank body is not a real message, and the reachability verdict must
        # not depend on what happened to be sent last.
        decision = self.limiter.probe_guards(contact_id, now=now)
        if decision.denied:
            return False, decision.detail
        return True, "available"

    # -- 3. receive ------------------------------------------------------

    def receive(
        self, *, now: Optional[datetime] = None, limit: int = 100
    ) -> InboundBatch:
        """Poll, validate, dedupe and apply control commands.

        Returns events for the *customer* (backend), failures for the log, and
        the transitions the commands caused. Once an event is returned it has
        already been applied to availability — the event is a fact, not a
        request, so a caller that crashes cannot lose a STOP.
        """
        now = self._now(now)
        since = self._last_poll_at
        if since is None:
            # First poll: do not replay the whole backlog as live events.
            since = now - timedelta(seconds=self.config.replay_window_seconds)
        else:
            # Overlap the previous window by a second: a message that arrived
            # in the same clock tick as the last poll must not be lost. The
            # dedupe set makes the re-read harmless.
            since = since - timedelta(seconds=1)
        try:
            raw = self.transport.fetch_inbound(since=since)
        except TransportError as exc:
            log.warning("inbound poll failed: %s", exc)
            return InboundBatch(polled_since=since)
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("inbound poll crashed: %s", exc)
            return InboundBatch(polled_since=since)

        events: list[InboundEvent] = []
        failures: list[ValidationFailure] = []
        transitions: list[tuple[str, Transition]] = []

        for item in list(raw)[:limit]:
            # A single malformed item must never abort the poll: convert each
            # one defensively and let validation decide.
            try:
                payload = item.as_payload() if hasattr(item, "as_payload") else item
            except Exception:
                payload = item
            if not isinstance(payload, Mapping):
                self._invalid += 1
                failures.append(
                    ValidationFailure(
                        "not_mapping", "inbound item could not be read as a message"
                    )
                )
                continue
            result = validate_inbound(
                payload,
                contact_index=self._contact_index,
                now=now,
                max_age_seconds=self.config.replay_window_seconds,
            )
            if isinstance(result, ValidationFailure):
                self._invalid += 1
                failures.append(result)
                continue
            if result.message_id in self._seen_ids:
                continue
            self._seen_ids.add(result.message_id)
            self._inbound += 1

            # Engagement resets anti-spam counters regardless of kind.
            self.limiter.record_inbound(result.sender.contact_id, now=now)

            if result.kind is InboundKind.COMMAND and result.command is not None:
                tr = self._apply_command(result.sender.contact_id, result.command, now=now)
                transitions.append((result.sender.contact_id, tr))
                events.append(result)
                # Acknowledge the command *immediately* — it is owed to the
                # person. Sent via send() with acknowledge= so it is exempt
                # from the limiter but ineligible for STOP suppression (they
                # just set STOP; ack is the one allowed message).
                self._send_ack(result.sender.contact_id, result.command, now=now)
            else:
                events.append(result)

        # Sweep expiring windows so the inspector's `since` is live.
        for exp in self.availability.expire_due(now):
            transitions.append(
                (
                    exp.contact_id,
                    Transition(exp.before, exp.after, changed=True, note="expired"),
                )
            )

        self._last_poll_at = now
        if len(self._seen_ids) > self.config.seen_message_capacity:
            self._seen_ids = set(list(self._seen_ids)[-self.config.seen_message_capacity // 2 :])

        return InboundBatch(
            events=tuple(events),
            failures=tuple(failures),
            transitions=tuple(transitions),
            polled_since=since,
        )

    def _apply_command(
        self, contact_id: str, command: ParsedCommand, *, now: datetime
    ) -> Transition:
        tr = self.availability.apply_command(contact_id, command, now=now)
        self.limiter.record_inbound_was_command(contact_id)
        return tr

    def _send_ack(
        self, contact_id: str, command: ParsedCommand, *, now: datetime
    ) -> Optional[OutboundReceipt]:
        if command.kind is CommandKind.RESUME:
            # No ack owed for RESUME: they want to be left alone-ish, not
            # chatted to. Keep it silent.
            return None
        return self.send(contact_id, "", acknowledge=command.kind, now=now)

    # -- 4. report -------------------------------------------------------

    def report(self) -> BridgeStatus:
        guards = {}
        for cid in self._contacts:
            guards[cid] = {
                **self.limiter.stats(cid),
                "availability": self.availability.snapshot(cid),
            }
        return BridgeStatus(
            mode=self._mode,
            transport="fake" if self.is_fake_transport else "mcp_stdio",
            linked_identity=self.config.linked_identity,
            sandbox=self.config.sandbox,
            sent_total=self._sent,
            suppressed_total=self._suppressed,
            refused_total=self._refused,
            failed_total=self._failed,
            inbound_total=self._inbound,
            invalid_inbound_total=self._invalid,
            guards=guards,
            last_poll_at=self._last_poll_at,
        )

    # -- helpers ---------------------------------------------------------

    def _now(self, now: Optional[datetime]) -> datetime:
        if now is None:
            return self._clock()
        return now if now.tzinfo else now.replace(tzinfo=timezone.utc)

    def sweep(self, *, now: Optional[datetime] = None) -> list[Transition]:
        """Explicit expiry sweep (for a scheduled job between polls)."""
        now = self._now(now)
        return [
            Transition(e.before, e.after, changed=True, note="expired")
            for e in self.availability.expire_due(now)
        ]


def _render_ack(kind: CommandKind, av: Availability) -> str:
    template = ACK_TEXT.get(kind, "")
    if kind is CommandKind.BUSY and av.is_stopped:
        # We received BUSY but STOP still wins; do not claim "marked busy".
        return (
            "You're still set to STOP, so I'm leaving you alone — send RESUME "
            "when you want messages again."
        )
    if kind is CommandKind.BUSY and av.expires_at is not None:
        minutes = max(1, int(round((av.expires_at - av.since).total_seconds() / 60)))
        duration = f"{minutes} min" if minutes < 120 else f"{minutes / 60:.1f} h".replace(".0 h", " h")
        return template.format(duration=duration)
    return template
