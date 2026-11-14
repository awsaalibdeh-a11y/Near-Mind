"""Transports — the only layer that touches WhatsApp.

Three implementations of one tiny protocol:

* :class:`WhatsAppTransport` — the protocol the rest of the bridge codes to.
* :class:`McpStdioTransport` — the real adapter over the workspace ``whatsapp``
  MCP server (``lharries/whatsapp-mcp``), speaking MCP JSON-RPC over stdio.
  It calls only the two MCP tools the bridge needs (``send_message`` and
  ``list_messages``); everything else stays in the upstream server.
* :class:`FakeTransport` — an in-memory transport with a scripted inbox and a
  full record of every "sent" message. No network, no account, no real send.
  Every test and the demo run against this.

The distinction that matters for the product: the MCP/Bridge transport talks
to *real people* on one linked account; the fake transport talks to *simulated
identities*. ``transport.is_fake`` is surfaced to the UI so the "sandbox vs
real bridge" badge is never a lie.

No phone numbers live in this module's public state. The MCP wants a recipient
in the WhatsApp wire format; the bridge passes the resolved wire key straight
through to the transport and never stores it in events.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Protocol, Sequence


@dataclass(frozen=True)
class TransportMessage:
    """A raw message as the transport knows it.

    ``sender_key`` is the opaque wire identifier (a JID). The bridge resolves
    it to a :class:`~bridge.events.ContactRef` before validating; this
    object never leaves the bridge.
    """

    message_id: str
    sender_key: str
    timestamp: datetime
    content: str = ""
    media_type: Optional[str] = None
    is_from_me: bool = False
    is_group: bool = False
    is_reaction: bool = False

    def as_payload(self) -> dict:
        """The mapping :func:`validate_inbound` consumes."""
        return {
            "id": self.message_id,
            "sender": self.sender_key,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "media_type": self.media_type,
            "is_from_me": self.is_from_me,
            "is_group": self.is_group,
            "is_reaction": self.is_reaction,
        }


class TransportError(RuntimeError):
    """A transport-level failure (server down, bad response, time-out)."""


class WhatsAppTransport(Protocol):
    """What the bridge needs from WhatsApp. Deliberately four methods."""

    is_fake: bool

    def send_text(self, recipient_key: str, body: str) -> str:
        """Send ``body``; return a transport message id. Raises TransportError."""
        ...

    def fetch_inbound(self, *, since: Optional[datetime]) -> Sequence[TransportMessage]:
        """Return messages that are *not* ours, received since ``since``."""
        ...

    def resolve_key(self, contact_id: str) -> Optional[str]:
        """Map an internal contact id to the wire recipient key, if known."""
        ...

    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# Fake transport
# ---------------------------------------------------------------------------


@dataclass
class SentRecord:
    recipient_key: str
    body: str
    sent_at: datetime
    message_id: str
    is_control_ack: bool = False


class FakeTransport:
    """Deterministic, in-memory transport for tests and the demo.

    Two modes:

    * **scripted** — the inbox is a list the test controls (``deliver``).
    * **dry-run send** — ``send_text`` never leaves the process; it appends to
      :attr:`sent` and returns a synthetic id. This is what proves the bridge
      end to end with no real send.
    """

    is_fake = True

    def __init__(
        self,
        contacts: Optional[dict[str, str]] = None,
        *,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        # contact_id -> wire key
        self._contacts = dict(contacts or {})
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.sent: list[SentRecord] = []
        self._inbox: list[TransportMessage] = []
        self._seq = 0
        self.closed = False

    # -- inbox control (used by tests) ----------------------------------

    def deliver(
        self,
        sender_key: str,
        content: str,
        *,
        media_type: Optional[str] = None,
        is_group: bool = False,
        is_reaction: bool = False,
        message_id: Optional[str] = None,
        at: Optional[datetime] = None,
    ) -> TransportMessage:
        self._seq += 1
        msg = TransportMessage(
            message_id=message_id or f"fake-in-{self._seq}",
            sender_key=sender_key,
            timestamp=at or self._clock(),
            content=content,
            media_type=media_type,
            is_group=is_group,
            is_reaction=is_reaction,
        )
        self._inbox.append(msg)
        self._record_resolved = getattr(self, "_record_resolved", True)
        self.recorded_keys.add(sender_key)
        return msg

    @property
    def recorded_keys(self) -> set[str]:
        if not hasattr(self, "_recorded_keys"):
            self._recorded_keys: set[str] = set()
        return self._recorded_keys

    def sent_to(self, contact_id: str) -> list[SentRecord]:
        key = self._contacts.get(contact_id)
        return [r for r in self.sent if r.recipient_key == key]

    # -- protocol --------------------------------------------------------

    def send_text(self, recipient_key: str, body: str) -> str:
        if self.closed:
            raise TransportError("fake transport is closed")
        if not recipient_key:
            raise TransportError("empty recipient")
        self._seq += 1
        mid = f"fake-out-{self._seq}"
        self.sent.append(
            SentRecord(
                recipient_key=recipient_key,
                body=body,
                sent_at=self._clock(),
                message_id=mid,
            )
        )
        return mid

    def fetch_inbound(self, *, since: Optional[datetime]) -> Sequence[TransportMessage]:
        out: list = []
        for m in self._inbox:
            # Tolerate junk items (tests inject them on purpose): a real
            # transport can hand back anything, and the poll must survive.
            try:
                if getattr(m, "is_from_me", False):
                    continue
                if since is not None and getattr(m, "timestamp", None) is not None:
                    if m.timestamp <= since:
                        continue
            except Exception:
                pass
            out.append(m)
        return out

    def resolve_key(self, contact_id: str) -> Optional[str]:
        return self._contacts.get(contact_id)

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# MCP stdio transport
# ---------------------------------------------------------------------------

#: Sent once, and only after an operator has flipped the live switch, to every
#: contact the bridge mirrors. Kept here so the text is reviewable in one place.
DRY_RUN_ONLY = "NearMind is running in dry-run mode on this account."


@dataclass
class _Pending:
    event: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: Optional[BaseException] = None


class McpStdioTransport:
    """Adapter over the workspace ``whatsapp`` MCP server.

    Speaks newline-delimited JSON-RPC 2.0 over the server's stdin/stdout — the
    same wire the MCP client the CLI uses speaks. Only two tools are called:

    * ``send_message(recipient, message)`` -> ``{success, message}``
    * ``list_messages(chat_jid=..., after=..., limit=..., ...)`` -> text
      formatter output (the upstream returns a formatted string, not JSON, so
      inbound polling is done per-chat by ``chat_jid`` and parsed leniently —
      see :meth:`fetch_inbound`).

    The server url/command is configuration, not code: ``stdio_command``.
    """

    is_fake = False

    def __init__(
        self,
        *,
        stdio_command: Sequence[str],
        env: Optional[dict[str, str]] = None,
        contacts: Optional[dict[str, str]] = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        if not stdio_command:
            raise ValueError("stdio_command is required to talk to the MCP server")
        self._command = list(stdio_command)
        self._env = {**os.environ, **(env or {})}
        self._contacts = dict(contacts or {})
        # A small internal cache of the most recent inbound per chat key, so
        # repeated polls do not re-emit the same messages.
        self._seen_ids: set[str] = set()
        self._timeout = timeout_seconds
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._pending: dict[int, _Pending] = {}
        self._next_id = 0
        self._reader: Optional[threading.Thread] = None
        self._stderr_tail: list[str] = []
        self._start()

    # -- process / framing ----------------------------------------------

    def _start(self) -> None:
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._env,
            text=True,
            bufsize=1,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        self._initialize()

    def _drain_stderr(self) -> None:
        assert self._proc and self._proc.stderr
        for line in self._proc.stderr:
            self._stderr_tail.append(line.rstrip())
            del self._stderr_tail[:-50]

    def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue  # server logs leaked to stdout; ignore
            if "id" in msg and msg.get("id") is not None:
                with self._lock:
                    pending = self._pending.pop(msg["id"], None)
                if pending is None:
                    continue
                if "error" in msg:
                    pending.error = TransportError(json.dumps(msg["error"]))
                else:
                    pending.result = msg.get("result")
                pending.event.set()

    def _write(self, obj: dict) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise TransportError("MCP server is not running")
        try:
            self._proc.stdin.write(json.dumps(obj) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise TransportError(f"MCP server pipe broke: {exc}") from exc

    def _request(self, method: str, params: Optional[dict] = None) -> Any:
        with self._lock:
            self._next_id += 1
            rid = self._next_id
            pending = _Pending()
            self._pending[rid] = pending
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            payload["params"] = params
        self._write(payload)
        if not pending.event.wait(self._timeout):
            with self._lock:
                self._pending.pop(rid, None)
            raise TransportError(f"MCP request {method!r} timed out")
        if pending.error is not None:
            raise TransportError(str(pending.error))
        return pending.result

    def _notify(self, method: str, params: Optional[dict] = None) -> None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._write(payload)

    def _initialize(self) -> None:
        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "nearmind-bridge", "version": "1.0"},
            },
        )
        self._notify("notifications/initialized")

    # -- protocol --------------------------------------------------------

    def send_text(self, recipient_key: str, body: str) -> str:
        result = self._request(
            "tools/call",
            {"name": "send_message", "arguments": {"recipient": recipient_key, "message": body}},
        )
        payload = _unwrap_tool_result(result)
        if not isinstance(payload, dict) or not payload.get("success"):
            detail = payload.get("message") if isinstance(payload, dict) else str(payload)
            raise TransportError(f"send_message failed: {detail}")
        # Upstream returns only success+message; synthesise a deterministic id
        # from the recipient and wall clock so the caller has an id shape.
        return f"mcp-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    def fetch_inbound(self, *, since: Optional[datetime]) -> Sequence[TransportMessage]:
        """Poll every mirrored 1:1 chat for messages newer than ``since``.

        The upstream ``list_messages`` returns a *formatted string* like
        ``[2026-11-14 01:45:00] Chat: X From: Name: body`` when
        ``include_context`` is off? — in fact it always formats. We ask for
        structured-ish data by calling per chat and parsing defensively; any
        line that does not parse is dropped rather than guessed at. The bridge's
        own :func:`validate_inbound` is the second line of defence.
        """
        out: list[TransportMessage] = []
        after = since.isoformat() if since else None
        for contact_id, wire_key in self._contacts.items():
            args = {
                "chat_jid": wire_key,
                "limit": 50,
                "include_context": False,
            }
            if after:
                args["after"] = after
            try:
                result = self._request(
                    "tools/call", {"name": "list_messages", "arguments": args}
                )
            except TransportError:
                continue  # one bad chat must not stop the poll
            text = _unwrap_tool_result(result)
            for line in str(text or "").splitlines():
                msg = _parse_formatted_line(line, wire_key)
                if msg is None or msg.message_id in self._seen_ids:
                    continue
                self._seen_ids.add(msg.message_id)
                out.append(msg)
        if len(self._seen_ids) > 5000:
            self._seen_ids = set(list(self._seen_ids)[-2500:])
        return out

    def resolve_key(self, contact_id: str) -> Optional[str]:
        return self._contacts.get(contact_id)

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
        except OSError:
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        self._proc = None


def _unwrap_tool_result(result: Any) -> Any:
    """MCP tool results are ``{content: [{type: text, text: ...}]}``.

    Some tools return already-ordered JSON. Try JSON first, fall back to text.
    """
    if result is None:
        return None
    if isinstance(result, (dict, list)):
        content = result.get("content") if isinstance(result, dict) else None
        if content is None:
            return result
        texts = [
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except (json.JSONDecodeError, TypeError):
            return joined
    return result


_FORMATTED_LINE = None  # compiled lazily below to keep import light


def _parse_formatted_line(line: str, wire_key: str) -> Optional[TransportMessage]:
    """Parse the upstream's ``[ts] Chat: X From: Y: body`` format defensively."""
    import re

    global _FORMATTED_LINE
    if _FORMATTED_LINE is None:
        _FORMATTED_LINE = re.compile(
            r"^\[(?P<ts>[^\]]+)\]\s*(?:Chat:\s*(?P<chat>[^\s].*?)\s+)?"
            r"From:\s*(?P<sender>.*?):\s*(?P<body>.*)$"
        )
    m = _FORMATTED_LINE.match(line.strip())
    if not m:
        return None
    ts_raw = m.group("ts").strip()
    try:
        ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    sender = m.group("sender").strip()
    body = m.group("body")
    # "Me" lines are our own sends — never inbound.
    is_from_me = sender in ("Me", "me")
    media_type = None
    # Upstream prefixes media as "[image - Message ID: X - Chat JID: Y] "
    if body.startswith("[") and "Message ID:" in body:
        try:
            media_type = body[1:].split(" - ", 1)[0].strip() or None
        except Exception:
            media_type = "media"
        body = ""
    import hashlib

    mid = "h-" + hashlib.blake2s(
        f"{sender}|{ts_raw}|{body}".encode("utf-8"), digest_size=8
    ).hexdigest()
    return TransportMessage(
        message_id=mid,
        sender_key=wire_key,
        timestamp=ts,
        content=body,
        media_type=media_type,
        is_from_me=is_from_me,
    )
