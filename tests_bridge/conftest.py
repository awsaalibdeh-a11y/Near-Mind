"""Shared fixtures for the bridge tests.

Everything is deterministic: an injected clock and the in-memory fake
transport. No network, no account, no real numbers.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Make `nearmind` importable without installing the package.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge.config import BridgeConfig, RateLimitConfig  # noqa: E402
from bridge.events import ContactRef  # noqa: E402
from bridge.transport import FakeTransport  # noqa: E402
from bridge.core import WhatsAppBridge  # noqa: E402


T0 = datetime(2026, 11, 14, 18, 0, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, start: datetime = T0) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> datetime:
        self.now = self.now + timedelta(**kwargs)
        return self.now


CONTACTS = {
    "karim": ContactRef("karim", "Karim"),
    "ali": ContactRef("ali", "Ali"),
    "umm_samir": ContactRef("umm_samir", "Umm Samir"),
}

# Clearly-fake wire keys. These are NOT phone numbers — they exist only to
# key the in-memory fake transport, and are never dialled.
WIRE = {
    "karim": "fake-karim@s.whatsapp.net",
    "ali": "fake-ali@s.whatsapp.net",
    "umm_samir": "fake-umm-samir@s.whatsapp.net",
}


@pytest.fixture()
def clock() -> Clock:
    return Clock()


@pytest.fixture()
def transport(clock) -> FakeTransport:
    return FakeTransport(WIRE, clock=clock)


@pytest.fixture()
def bridge(clock, transport) -> WhatsAppBridge:
    cfg = BridgeConfig(
        linked_identity="NearMind linked account (test)",
        sandbox=True,
    )
    b = WhatsAppBridge(config=cfg, transport=transport, contacts=CONTACTS, clock=clock)
    # First poll primes the replay window so later scripted messages read live.
    b.receive(now=clock())
    return b


@pytest.fixture()
def tight_config() -> BridgeConfig:
    """Small limits so rate-limit boundaries are fast to hit."""
    return BridgeConfig(
        rate_limits=RateLimitConfig(
            burst_capacity=3,
            burst_refill_seconds=30,
            daily_capacity=5,
            daily_window_seconds=24 * 3600,
            silence_after_unanswered=2,
            backoff_base_seconds=600,
            backoff_max_seconds=3600,
            max_unanswered_before_refusal=4,
            repeat_window_seconds=900,
        )
    )
