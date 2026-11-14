"""Bridge configuration — every knob that limits what NearMind may do to a
real person is here, as a dataclass with a commented default.

The numbers on this class are product decisions, not implementation detail.
Each one is justified inline and again in ``docs/BRIDGE.md`` §4. They are
deliberately conservative: the failure mode of an over-eager agent is a
neighbour blocking the number, and a blocked number loses the whole product.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RateLimitConfig:
    """Per-contact outbound budget.

    Two layers, because each stops a different failure:

    * **burst** — a token bucket. Stops a runaway loop firing ten messages in
      two seconds while the person is still reading the first. Four tokens
      refilling at one per 60 s is faster than any reasonable favour thread.
    * **volume** — a hard rolling 24 h cap. Stops the *slow* spam the bucket
      misses: one message every ten minutes for eight hours. Five per day is
      one favour thread (ask -> clarify -> confirm -> handover -> release)
      with a message of slack.

    Plus silence backoff, duplicate suppression and a hard refusal after too
    many unanswered messages. See the fields below.
    """

    # Burst bucket.
    burst_capacity: int = 4
    burst_refill_seconds: float = 60.0  # one token per 60 s

    # Rolling daily cap (24 h window).
    daily_capacity: int = 5
    daily_window_seconds: int = 24 * 3600

    # Silence backoff.
    silence_after_unanswered: int = 2
    backoff_base_seconds: int = 10 * 60     # first backoff: 10 min
    backoff_max_seconds: int = 6 * 3600     # never wait more than 6 h
    max_unanswered_before_refusal: int = 4  # after this, stop sending entirely

    # Duplicate protection.
    repeat_window_seconds: int = 15 * 60


@dataclass(frozen=True)
class AvailabilityConfig:
    """Availability windows and command semantics."""

    #: If a person sends a bare ``BUSY`` we hold them busy for this long. One
    #: hour is the modal "I'm cooking / on a call" answer; they can shorten it
    #: with ``busy 20m`` or lift it instantly with ``resume``.
    default_busy_seconds: int = 60 * 60

    #: Ceiling on any self-declared window (``busy 2d`` is clamped).
    max_busy_seconds: int = 12 * 3600

    #: A ``STOP`` with a duration (``stop 2h``) is honoured as STOP-with-expiry
    #: rather than a sticky STOP. The anti-spam rule applies while it lasts.
    allow_timed_stop: bool = True

    #: When a BUSY window expires, the person returns to ``available`` (not to
    #: whatever they were before) unless that earlier state was STOP. This is
    #: what makes BUSY "temporary" and STOP "sticky".
    busy_expiry_returns_to_available: bool = True


@dataclass(frozen=True)
class BridgeConfig:
    """Everything the bridge needs to be constructed.

    ``linked_identity`` is the display name of the single WhatsApp account the
    bridge is linked to — used only for the honest-identity banner and logs.
    It is never used to route messages (routing is by contact map).
    """

    linked_identity: str = "NearMind (linked account)"
    #: The demo is a *sandbox* until a real number is deliberately linked. The
    #: UI reads this to render the honest badge (see docs/BRIDGE.md §6).
    sandbox: bool = True

    rate_limits: RateLimitConfig = field(default_factory=RateLimitConfig)
    availability: AvailabilityConfig = field(default_factory=AvailabilityConfig)

    #: If True, the transport is never asked to actually deliver. The
    #: :class:`~bridge.transport.FakeTransport` is used instead and
    #: every "send" is recorded. This is the default and the only mode that
    #: exists until an operator sets ``allow_live_sends`` after the gate in
    #: ``docs/BRIDGE.md`` §7.
    dry_run: bool = True

    #: Explicit operator confirmation that a live send to real numbers is
    #: permitted. Both ``dry_run=False`` **and** this must be true; either one
    #: alone leaves the bridge in dry-run. This is the gate the acceptance
    #: criteria refer to.
    allow_live_sends: bool = False

    #: Messages older than this on first connect are not replayed as live
    #: events (they could re-trigger a STOP that was already lifted).
    replay_window_seconds: int = 6 * 3600

    #: How many message ids to remember for de-duplication of inbound polls.
    seen_message_capacity: int = 500

    #: Optional IANA timezone for rendering "local time" in decision reasons.
    timezone: str = "Europe/Amsterdam"

    def effective_dry_run(self) -> bool:
        """Dry-run unless *both* switches are flipped. Fail closed."""
        return self.dry_run or not self.allow_live_sends
