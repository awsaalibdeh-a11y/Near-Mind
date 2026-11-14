"""Per-contact rate limiting and anti-spam for outbound messages.

The limiter answers exactly one question: *"may I send this message to this
contact right now?"* — and when the answer is no, it says *why* and *when* the
answer might change. It knows nothing about WhatsApp; the bridge asks before
every send.

Layers, in the order they are checked (the order matters — the most absolute
refusal is checked first, so the reason a caller gets is the most important
one):

1. **duplicate** — the identical body to the same contact inside the repeat
   window. Always refused; a retry that repeats itself reads as a broken bot.
2. **hard day cap** — ``daily_capacity`` sends in a rolling 24 h window.
3. **unanswered refusal** — after ``max_unanswered_before_refusal`` messages
   the contact never answered, stop sending entirely. This is the "no
   repeated pinging" rule's final form.
4. **bounce bucket** — ``burst_capacity`` tokens refilling at one per
   ``burst_refill_seconds``. Stops bursts.
5. **silence backoff** — after ``silence_after_unanswered`` unanswered
   messages, require an exponentially growing gap since the last send.

A refusal carries ``retry_after_seconds`` so the bridge can schedule a
check-back rather than hammer. ``None`` retry means "not by waiting" (e.g.
duplicate, or the unanswered ceiling — a person's silence is the signal, not a
timer).
"""

from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Deque, Optional

from .config import RateLimitConfig


class SendRefusal(str, Enum):
    """Stable slugs the backend can switch on (and put in decision logs)."""

    DUPLICATE = "duplicate"
    DAY_CAP = "day_cap"
    UNANSWERED_CEILING = "unanswered_ceiling"
    BURST = "burst"
    SILENCE_BACKOFF = "silence_backoff"


@dataclass(frozen=True)
class RateDecision:
    """Allow/deny plus the reason and the earliest useful retry."""

    allowed: bool
    #: Populated only when ``allowed`` is False.
    refusal: Optional[SendRefusal] = None
    detail: str = ""
    #: Seconds until this exact send might succeed; ``None`` = not by waiting.
    retry_after_seconds: Optional[int] = None
    #: Diagnostics, in the shape the dashboard likes.
    burst_tokens_left: float = 0.0
    daily_used: int = 0
    unanswered: int = 0

    @property
    def denied(self) -> bool:
        return not self.allowed


@dataclass
class _ContactState:
    #: timestamps of every accepted send (rolling window trimmed on use)
    sends: Deque[datetime] = None  # type: ignore[assignment]
    #: fractional tokens available in the bucket
    tokens: float = 0.0
    tokens_updated_at: Optional[datetime] = None
    last_send_at: Optional[datetime] = None
    last_body_digest: Optional[str] = None
    unanswered: int = 0

    def __post_init__(self) -> None:
        if self.sends is None:
            self.sends = deque()


def _digest(body: str) -> str:
    return hashlib.blake2s(body.strip().encode("utf-8"), digest_size=8).hexdigest()


class RateLimiter:
    """Rolling-window limiter. Injected clock; deterministic under test."""

    def __init__(self, config: RateLimitConfig, *, clock=None) -> None:
        self.config = config
        self._states: dict[str, _ContactState] = {}
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # -- internal --------------------------------------------------------

    def _now(self, now: Optional[datetime]) -> datetime:
        if now is None:
            return self._clock()
        return now if now.tzinfo else now.replace(tzinfo=timezone.utc)

    def _state(self, contact_id: str, now: datetime) -> _ContactState:
        st = self._states.get(contact_id)
        if st is None:
            st = _ContactState(tokens=float(self.config.burst_capacity))
            st.tokens_updated_at = now
            self._states[contact_id] = st
        # Trim the daily window and refill the bucket lazily.
        horizon = now - timedelta(seconds=self.config.daily_window_seconds)
        while st.sends and st.sends[0] < horizon:
            st.sends.popleft()
        if st.tokens_updated_at is not None and self.config.burst_refill_seconds > 0:
            elapsed = (now - st.tokens_updated_at).total_seconds()
            if elapsed > 0:
                refill = elapsed / self.config.burst_refill_seconds
                st.tokens = min(
                    float(self.config.burst_capacity), st.tokens + refill
                )
                st.tokens_updated_at = now
        return st

    # -- public ----------------------------------------------------------

    def decide(
        self,
        contact_id: str,
        body: str,
        *,
        now: Optional[datetime] = None,
    ) -> RateDecision:
        """Decide without consuming a token (a dry-run check)."""
        now = self._now(now)
        st = self._state(contact_id, now)
        return self._decide_with_state(st, contact_id, body, now)

    def probe_guards(
        self, contact_id: str, *, now: Optional[datetime] = None
    ) -> RateDecision:
        """Reachability probe: every guard *except* duplicate.

        Used by the agent's eligibility filter, where the question is "would a
        normal message get through", not "would this exact body".
        """
        now = self._now(now)
        st = self._state(contact_id, now)
        return self._decide_with_state(st, contact_id, "", now, skip_duplicate=True)

    def check_and_consume(
        self,
        contact_id: str,
        body: str,
        *,
        now: Optional[datetime] = None,
    ) -> RateDecision:
        """Decide and, if allowed, consume the budget for this send."""
        now = self._now(now)
        st = self._state(contact_id, now)
        decision = self._decide_with_state(st, contact_id, body, now)
        if decision.allowed:
            st.sends.append(now)
            st.tokens -= 1.0
            st.last_send_at = now
            st.last_body_digest = _digest(body)
        return decision

    def record_inbound(self, contact_id: str, *, now: Optional[datetime] = None) -> None:
        """A reply arrived: reset the unanswered counter (they are engaged)."""
        now = self._now(now)
        st = self._state(contact_id, now)
        st.unanswered = 0

    def record_inbound_was_command(self, contact_id: str) -> None:
        """STOP/BUSY also count as engagement for anti-spam purposes.

        Not used to lift STOP — availability owns that — only to say the
        person is not ghosting us.
        """
        st = self._states.get(contact_id)
        if st is not None:
            st.unanswered = 0

    def register_outbound(
        self, contact_id: str, body: str, *, now: Optional[datetime] = None
    ) -> None:
        """Record a send made *outside* this limiter's guard (never for normal
        sends): a command acknowledgement the bridge exempted. Still counts
        against volume so a loop of acks cannot spam.
        """
        now = self._now(now)
        st = self._state(contact_id, now)
        st.sends.append(now)
        st.last_send_at = now
        st.last_body_digest = _digest(body)

    def mark_unanswered(self, contact_id: str) -> None:
        """Called by the bridge after a send that did not get a reply yet.

        The bridge calls :meth:`record_inbound` on any inbound; whichever comes
        last wins because both read the same counter. The counter is a proxy
        for "messages since they last spoke"; incrementing on send and zeroing
        on reply is exactly that.
        """
        st = self._states.get(contact_id)
        if st is not None:
            st.unanswered += 1

    # -- the decision tree ----------------------------------------------

    def _decide_with_state(
        self,
        st: _ContactState,
        contact_id: str,
        body: str,
        now: datetime,
        *,
        skip_duplicate: bool = False,
    ) -> RateDecision:
        cfg = self.config
        tokens = st.tokens
        daily_used = len(st.sends)

        # 1. duplicate
        if (
            not skip_duplicate
            and cfg.repeat_window_seconds > 0
            and st.last_body_digest == _digest(body)
            and st.last_send_at is not None
            and (now - st.last_send_at).total_seconds() < cfg.repeat_window_seconds
        ):
            wait = int(cfg.repeat_window_seconds - (now - st.last_send_at).total_seconds())
            return RateDecision(
                False,
                SendRefusal.DUPLICATE,
                detail=(
                    f"identical message to {contact_id} within "
                    f"{cfg.repeat_window_seconds // 60} min — not repeated"
                ),
                retry_after_seconds=max(1, wait),
                burst_tokens_left=tokens,
                daily_used=daily_used,
                unanswered=st.unanswered,
            )

        # 2. day cap
        if daily_used >= cfg.daily_capacity:
            oldest = st.sends[0]
            retry = int(
                (oldest + timedelta(seconds=cfg.daily_window_seconds) - now).total_seconds()
            )
            return RateDecision(
                False,
                SendRefusal.DAY_CAP,
                detail=(
                    f"{contact_id} already received {daily_used} messages today "
                    f"(cap {cfg.daily_capacity})"
                ),
                retry_after_seconds=max(1, retry),
                burst_tokens_left=tokens,
                daily_used=daily_used,
                unanswered=st.unanswered,
            )

        # 3. unanswered ceiling
        if st.unanswered >= cfg.max_unanswered_before_refusal:
            return RateDecision(
                False,
                SendRefusal.UNANSWERED_CEILING,
                detail=(
                    f"{contact_id} has not answered the last {st.unanswered} messages; "
                    "not pinging again"
                ),
                retry_after_seconds=None,
                burst_tokens_left=tokens,
                daily_used=daily_used,
                unanswered=st.unanswered,
            )

        # 4. burst bucket
        if tokens < 1.0:
            deficit = 1.0 - tokens
            retry = int(deficit * cfg.burst_refill_seconds) + 1
            return RateDecision(
                False,
                SendRefusal.BURST,
                detail=(
                    f"burst limit for {contact_id}: {cfg.burst_capacity} messages per "
                    f"{int(cfg.burst_refill_seconds)} s; retry in ~{retry} s"
                ),
                retry_after_seconds=retry,
                burst_tokens_left=tokens,
                daily_used=daily_used,
                unanswered=st.unanswered,
            )

        # 5. silence backoff
        if (
            st.unanswered >= cfg.silence_after_unanswered
            and st.last_send_at is not None
        ):
            over = st.unanswered - cfg.silence_after_unanswered
            required = min(
                cfg.backoff_base_seconds * (2 ** over), cfg.backoff_max_seconds
            )
            since = (now - st.last_send_at).total_seconds()
            if since < required:
                retry = int(required - since) + 1
                return RateDecision(
                    False,
                    SendRefusal.SILENCE_BACKOFF,
                    detail=(
                        f"{contact_id} has not replied to the last {st.unanswered} "
                        f"messages; waiting until {_fmt_delay(required)} after the "
                        "last one before the next"
                    ),
                    retry_after_seconds=retry,
                    burst_tokens_left=tokens,
                    daily_used=daily_used,
                    unanswered=st.unanswered,
                )

        return RateDecision(
            True,
            None,
            detail="allowed",
            retry_after_seconds=0,
            burst_tokens_left=tokens,
            daily_used=daily_used,
            unanswered=st.unanswered,
        )

    # -- diagnostics -----------------------------------------------------

    def stats(self, contact_id: str, *, now: Optional[datetime] = None) -> dict:
        now = self._now(now)
        st = self._state(contact_id, now)
        return {
            "contact_id": contact_id,
            "daily_used": len(st.sends),
            "daily_capacity": self.config.daily_capacity,
            "burst_tokens": round(st.tokens, 2),
            "burst_capacity": self.config.burst_capacity,
            "unanswered": st.unanswered,
        }


def _fmt_delay(seconds: int) -> str:
    if seconds >= 3600:
        return f"{seconds / 3600:.1f} h".replace(".0 h", " h")
    return f"{int(seconds / 60)} min"
