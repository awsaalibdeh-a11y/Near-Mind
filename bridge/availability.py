"""The availability state machine.

A neighbour has exactly one :class:`AvailabilityState` at a time:

    AVAILABLE  -- can take a request now
    BUSY       -- present but not free; has a window that expires on its own
    NOT_AT_HOME -- out of the building; never reachable

and STOP is modelled as **sticky unavailability**: a STOP sets ``NOT_AT_HOME``
with ``source="whatsapp_stop"`` and *no expiry*, and only an explicit RESUME
lifts it. That keeps one state enum on the wire (the UI contract in LEG-434
asks for exactly ``available | busy | not_at_home``) while preserving the two
distinct behaviours the product requires:

* BUSY is a **window**: it carries ``expires_at`` and returns to AVAILABLE on
  its own. ``expire(now)`` sweeps it.
* STOP is **sticky**: ``expires_at is None`` until they say ``resume`` (or a
  timed ``stop 2h``, which is honoured as an expiring stop).

Separately, ``asleep`` is an independent fact (home-but-asleep is real). This
class does *not* model sleep — it lives with the clock — but
:func:`is_reachable` takes it in so callers cannot accidentally treat a
sleeping neighbour as reachable without saying so.

All transitions are **idempotent** and **total**: every method accepts any
command at any time, including ``BUSY`` while already busy, ``STOP`` while
already stopped, and ``RESUME`` when already available. A transition always
produces an :class:`Availability` snapshot plus a boolean ``changed`` so the
caller can log only real changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional

from .commands import CommandKind, ParsedCommand


class AvailabilityState(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    NOT_AT_HOME = "not_at_home"


class AvailabilitySource(str, Enum):
    #: Set by the sandbox / scripted scenario.
    SANDBOX = "sandbox"
    #: The person texted STOP (or an equivalent).
    WHATSAPP_STOP = "whatsapp_stop"
    #: The person texted BUSY (or an equivalent).
    WHATSAPP_BUSY = "whatsapp_busy"
    #: They explicitly resumed.
    WHATSAPP_RESUME = "whatsapp_resume"
    #: A BUSY window expired on its own.
    BUSY_EXPIRED = "busy_expired"
    #: A timed STOP window expired on its own.
    STOP_EXPIRED = "stop_expired"
    #: The person said they are leaving (out of building) via a future flow.
    WHATSAPP_OUT = "whatsapp_out"


@dataclass(frozen=True)
class Availability:
    """A neighbour's availability at one instant.

    ``reason`` and ``since`` are mandatory for anything that is not
    ``available`` — that is the inspector's entire value ("why, and since
    when").
    """

    state: AvailabilityState
    source: AvailabilitySource
    since: datetime
    reason: str
    expires_at: Optional[datetime] = None

    #: True when a STOP is in force. This is what the rate limiter and the
    #: outbound guard check to suppress *all* non-control messages.
    @property
    def is_stopped(self) -> bool:
        return self.source is AvailabilitySource.WHATSAPP_STOP and self.state in (
            AvailabilityState.NOT_AT_HOME,
            AvailabilityState.BUSY,
        )

    @property
    def is_busy(self) -> bool:
        return self.state is AvailabilityState.BUSY

    @property
    def is_out(self) -> bool:
        return self.state is AvailabilityState.NOT_AT_HOME

    @property
    def is_available(self) -> bool:
        return self.state is AvailabilityState.AVAILABLE


def available(since: datetime) -> Availability:
    return Availability(
        state=AvailabilityState.AVAILABLE,
        source=AvailabilitySource.SANDBOX,
        since=since,
        reason="Available",
        expires_at=None,
    )


def not_at_home(reason: str, since: datetime, *, stopped: bool) -> Availability:
    return Availability(
        state=AvailabilityState.NOT_AT_HOME,
        source=AvailabilitySource.WHATSAPP_STOP if stopped else AvailabilitySource.SANDBOX,
        since=since,
        reason=reason,
        expires_at=None,
    )


@dataclass(frozen=True)
class Transition:
    """The result of applying one event to one contact."""

    before: Availability
    after: Availability
    changed: bool
    #: Set if the event was ignored (idempotent no-op or stale/expired).
    note: Optional[str] = None


@dataclass(frozen=True)
class ExpiryResult:
    """Outcome of sweeping expiring windows at a point in time."""

    contact_id: str
    before: Availability
    after: Availability

    @property
    def changed(self) -> bool:
        return self.before != self.after


class AvailabilityStore:
    """Per-contact availability, keyed by opaque contact id.

    The store is the single owner of "may NearMind message this person right
    now". The backend should call :meth:`may_contact` (or read
    :meth:`get`) before every outreach and log the reason.

    Time is *injected* (``now`` argument) so tests and the scripted sandbox are
    fully deterministic — no ``datetime.now()`` inside the state machine.
    """

    def __init__(
        self,
        *,
        default_busy_seconds: int = 60 * 60,
        max_busy_seconds: int = 12 * 3600,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._entries: dict[str, Availability] = {}
        self.default_busy_seconds = default_busy_seconds
        self.max_busy_seconds = max_busy_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # -- reads -----------------------------------------------------------

    def _now(self, now: Optional[datetime]) -> datetime:
        if now is None:
            return self._clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now

    def ensure(self, contact_id: str, now: Optional[datetime] = None) -> Availability:
        """Return the current availability, materialising AVAILABLE on first use.

        Expiring windows are swept lazily on read, so no background job is
        required for correctness — the bridge *also* sweeps on its poll tick
        so the dashboard's ``since`` timestamps stay live.
        """
        now = self._now(now)
        current = self._entries.get(contact_id)
        if current is None:
            current = available(now)
            self._entries[contact_id] = current
            return current
        swept = self._sweep_one(contact_id, now)
        return swept.after

    def get(self, contact_id: str, now: Optional[datetime] = None) -> Availability:
        return self.ensure(contact_id, now)

    def may_contact(
        self, contact_id: str, *, now: Optional[datetime] = None, asleep: bool = False
    ) -> tuple[bool, str]:
        """Whether an outreach is allowed, with a human reason either way.

        Returns ``(allowed, reason)``. The reason is written for a decision
        log, e.g. *"Karim sent STOP at 14:03 — not messaged until he resumes."*
        """
        av = self.ensure(contact_id, now)
        if av.is_stopped:
            return False, (
                f"{contact_id} sent STOP — not messaged again until they resume"
            )
        if av.state is AvailabilityState.NOT_AT_HOME:
            return False, f"{contact_id} is not at home ({av.reason})"
        if av.state is AvailabilityState.BUSY:
            until = av.expires_at.strftime("%H:%M") if av.expires_at else "later"
            return False, f"{contact_id} is busy ({av.reason}), free again around {until}"
        if asleep:
            return False, f"{contact_id} is at home but asleep ({av.reason})"
        return True, "available"

    def all(self, now: Optional[datetime] = None) -> dict[str, Availability]:
        now = self._now(now)
        for cid in list(self._entries):
            self._sweep_one(cid, now)
        return dict(self._entries)

    def snapshot(self, contact_id: str, now: Optional[datetime] = None) -> dict:
        """The wire shape the UI's inspector expects (LEG-434 §3)."""
        av = self.ensure(contact_id, now)
        return {
            "state": av.state.value,
            "reason": av.reason,
            "since": av.since.isoformat(),
            "source": av.source.value,
            "expires_at": av.expires_at.isoformat() if av.expires_at else None,
        }

    # -- writes ----------------------------------------------------------

    def apply_command(
        self,
        contact_id: str,
        command: ParsedCommand,
        *,
        now: Optional[datetime] = None,
    ) -> Transition:
        """Apply a parsed control command. Total and idempotent.

        * ``STOP``        -> NOT_AT_HOME (sticky), or BUSY-with-expiry if timed
        * ``BUSY``        -> BUSY with an expiry (default 1 h, clamped)
        * ``RESUME``      -> AVAILABLE
        * ``HELP``        -> no state change
        """
        now = self._now(now)
        before = self.ensure(contact_id, now)

        if command.kind is CommandKind.HELP:
            return Transition(before, before, changed=False, note="help request; no state change")

        if command.kind is CommandKind.RESUME:
            after = available(now)
            self._entries[contact_id] = after
            changed = not _same_state(before, after)
            return Transition(before, after, changed, None if changed else "already available")

        if command.kind is CommandKind.BUSY:
            # A BUSY can never weaken a sticky STOP. If they are stopped and
            # text "busy 30m", the only safe reading is "still stopped, and
            # also busy" — but we cannot represent two states, and losing the
            # STOP would make us message a person who said stop. So the STOP
            # stays; we refresh its `since` reason to note the busy signal.
            if before.is_stopped:
                return Transition(
                    before,
                    before,
                    changed=False,
                    note="BUSY received while stopped; STOP takes precedence",
                )
            seconds = _clamp(
                command.duration_seconds or self.default_busy_seconds, self.max_busy_seconds
            )
            after = Availability(
                state=AvailabilityState.BUSY,
                source=AvailabilitySource.WHATSAPP_BUSY,
                since=now,
                reason=f"Texted BUSY ({_human_duration(seconds)})",
                expires_at=now + timedelta(seconds=seconds),
            )
            self._entries[contact_id] = after
            return Transition(before, after, changed=True)

        # STOP
        if command.duration_seconds:
            seconds = _clamp(command.duration_seconds, self.max_busy_seconds)
            # A timed STOP *is* a stop: it carries the anti-spam rule while it
            # lasts, so it must be BUSY-state but STOP-sourced.
            after = Availability(
                state=AvailabilityState.BUSY,
                source=AvailabilitySource.WHATSAPP_STOP,
                since=now,
                reason=f"Texted STOP for {_human_duration(seconds)}",
                expires_at=now + timedelta(seconds=seconds),
            )
            self._entries[contact_id] = after
            return Transition(before, after, changed=True)

        after = Availability(
            state=AvailabilityState.NOT_AT_HOME,
            source=AvailabilitySource.WHATSAPP_STOP,
            since=now,
            reason="Texted STOP — unreachable until they resume",
            expires_at=None,
        )
        # Idempotent: a second bare STOP returns the *original* since so the
        # inspector does not claim they stopped again at a new time.
        if before.is_stopped and before.expires_at is None:
            return Transition(before, before, changed=False, note="already stopped")
        self._entries[contact_id] = after
        return Transition(before, after, changed=True)

    def set_sandbox_state(
        self,
        contact_id: str,
        state: AvailabilityState | str,
        *,
        reason: str,
        now: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> Transition:
        """Scripted/sandbox state, e.g. "out — at the gym".

        A sandbox write **cannot override a STOP**: a real person's STOP
        outranks a scenario, otherwise a scripted run could quietly spam
        someone who told us to stop. Returns an unchanged transition with a
        note in that case.
        """
        now = self._now(now)
        before = self.ensure(contact_id, now)
        if before.is_stopped:
            return Transition(
                before, before, changed=False, note="sandbox state ignored: contact has STOPped"
            )
        state = AvailabilityState(state)
        after = Availability(
            state=state,
            source=AvailabilitySource.SANDBOX,
            since=now,
            reason=reason,
            expires_at=expires_at if state is AvailabilityState.BUSY else None,
        )
        self._entries[contact_id] = after
        return Transition(before, after, changed=not _same_state(before, after))

    # -- expiry ----------------------------------------------------------

    def expire_due(self, now: Optional[datetime] = None) -> list[ExpiryResult]:
        """Sweep every window that has elapsed. Returns the ones that changed."""
        now = self._now(now)
        results: list[ExpiryResult] = []
        for cid, av in list(self._entries.items()):
            before = av
            self._sweep_one(cid, now)
            after = self._entries[cid]
            if before != after:
                results.append(ExpiryResult(cid, before, after))
        return results

    def _sweep_one(self, contact_id: str, now: datetime) -> ExpiryResult:
        av = self._entries[contact_id]
        if av.expires_at is None or now < av.expires_at:
            return ExpiryResult(contact_id, av, av)
        if av.source is AvailabilitySource.WHATSAPP_STOP:
            after = Availability(
                state=AvailabilityState.AVAILABLE,
                source=AvailabilitySource.STOP_EXPIRED,
                since=av.expires_at,
                reason="Timed STOP expired — available again",
                expires_at=None,
            )
        else:
            after = Availability(
                state=AvailabilityState.AVAILABLE,
                source=AvailabilitySource.BUSY_EXPIRED,
                since=av.expires_at,
                reason="Busy window ended — available again",
                expires_at=None,
            )
        self._entries[contact_id] = after
        return ExpiryResult(contact_id, av, after)

    # -- introspection for the guard ------------------------------------

    def is_suppressed(self, contact_id: str, now: Optional[datetime] = None) -> bool:
        """True if *any* send other than a command acknowledgement must stop."""
        av = self.ensure(contact_id, now)
        return av.is_stopped or av.state is AvailabilityState.NOT_AT_HOME


def _same_state(a: Availability, b: Availability) -> bool:
    return (a.state, a.source, a.expires_at) == (b.state, b.source, b.expires_at)


def _clamp(seconds: int, ceiling: int) -> int:
    return max(1, min(int(seconds), ceiling))


def _human_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        hours = seconds // 3600
        return f"{hours} h"
    if seconds % 60 == 0:
        return f"{seconds // 60} min"
    return f"{seconds} s"
