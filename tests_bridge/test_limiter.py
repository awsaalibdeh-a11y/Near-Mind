"""Rate-limit boundaries, silence backoff and duplicate suppression."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone

from bridge.config import RateLimitConfig
from bridge.limiter import RateLimiter, SendRefusal

T = datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc)


def make(**over) -> tuple[RateLimiter, list[str], datetime]:
    cfg = RateLimitConfig(
        burst_capacity=3,
        burst_refill_seconds=60,
        daily_capacity=5,
        daily_window_seconds=24 * 3600,
        silence_after_unanswered=2,
        backoff_base_seconds=600,
        backoff_max_seconds=3600,
        max_unanswered_before_refusal=4,
        repeat_window_seconds=900,
    )
    cfg = dataclasses.replace(cfg, **over)
    now = [T]
    lim = RateLimiter(cfg, clock=lambda: now[0])
    bodies = [f"msg {i}" for i in range(50)]
    return lim, bodies, now


def test_burst_boundary_is_exact():
    lim, bodies, now = make()
    for i in range(3):
        d = lim.check_and_consume("karim", bodies[i], now=now[0])
        assert d.allowed, d.detail
    d = lim.check_and_consume("karim", bodies[3], now=now[0])
    assert d.denied and d.refusal is SendRefusal.BURST
    assert d.retry_after_seconds and d.retry_after_seconds > 0


def test_burst_refills_over_time():
    lim, bodies, now = make()
    for i in range(3):
        lim.check_and_consume("karim", bodies[i], now=now[0])
    now[0] = now[0] + timedelta(seconds=60)
    d = lim.check_and_consume("karim", bodies[10], now=now[0])
    assert d.allowed


def test_daily_cap_is_hard_even_over_a_long_day():
    lim, bodies, now = make(burst_refill_seconds=1)
    sends = 0
    for minute in range(0, 24 * 60, 2):  # one attempt every 2 minutes
        now[0] = T + timedelta(minutes=minute)
        d = lim.check_and_consume("karim", f"m{minute}", now=now[0])
        if d.allowed:
            sends += 1
            lim.record_inbound("karim", now=now[0])  # they answer each time
    assert sends == 5


def test_daily_window_rolls_off():
    lim, bodies, now = make(burst_refill_seconds=1, daily_capacity=2)
    for i in range(2):
        lim.check_and_consume("karim", bodies[i], now=now[0])
        lim.record_inbound("karim", now=now[0])
    now[0] = now[0] + timedelta(hours=25)
    d = lim.check_and_consume("karim", "fresh", now=now[0])
    assert d.allowed


def test_duplicate_body_is_suppressed():
    lim, bodies, now = make()
    assert lim.check_and_consume("karim", "same", now=now[0]).allowed
    d = lim.check_and_consume("karim", "  same  ", now=now[0])
    assert d.denied and d.refusal is SendRefusal.DUPLICATE


def test_duplicate_window_expires():
    lim, bodies, now = make()
    lim.check_and_consume("karim", "same", now=now[0])
    now[0] = now[0] + timedelta(seconds=901)
    lim.record_inbound("karim", now=now[0])
    assert lim.check_and_consume("karim", "same", now=now[0]).allowed


def test_silence_backoff_grows_and_then_refuses():
    """Traced sequence:

    18:00 a sent  (unanswered 1)
    18:01 b sent  (unanswered 2)
    18:02 c denied: 10 min gap required after b
    18:12 c sent  (unanswered 3)  -> next requires 20 min after c
    18:22 d denied (only 10 min since c)
    18:32 e sent  (unanswered 4)  -> hard refusal, not by waiting
    """
    lim, bodies, now = make()

    lim.check_and_consume("karim", "a", now=now[0]); lim.mark_unanswered("karim")
    now[0] += timedelta(seconds=61)
    lim.check_and_consume("karim", "b", now=now[0]); lim.mark_unanswered("karim")

    now[0] += timedelta(seconds=61)
    d = lim.check_and_consume("karim", "c", now=now[0])
    assert d.denied and d.refusal is SendRefusal.SILENCE_BACKOFF
    assert 0 < d.retry_after_seconds <= 600

    now[0] += timedelta(seconds=600)
    assert lim.check_and_consume("karim", "c", now=now[0]).allowed
    lim.mark_unanswered("karim")

    now[0] += timedelta(seconds=601)
    d = lim.check_and_consume("karim", "d", now=now[0])
    assert d.denied and d.refusal is SendRefusal.SILENCE_BACKOFF
    assert 500 < d.retry_after_seconds <= 600  # ~10 min of the 20 left

    now[0] += timedelta(seconds=601)
    assert lim.check_and_consume("karim", "e", now=now[0]).allowed
    lim.mark_unanswered("karim")

    now[0] += timedelta(days=1)
    d = lim.check_and_consume("karim", "f", now=now[0])
    assert d.denied and d.refusal is SendRefusal.UNANSWERED_CEILING
    assert d.retry_after_seconds is None


def test_inbound_reply_resets_unanswered():
    lim, bodies, now = make()
    lim.check_and_consume("karim", "a", now=now[0])
    lim.mark_unanswered("karim")
    lim.record_inbound("karim", now=now[0])
    now[0] += timedelta(seconds=61)
    assert lim.check_and_consume("karim", "b", now=now[0]).allowed


def test_contacts_are_isolated():
    lim, bodies, now = make()
    for i in range(3):
        lim.check_and_consume("karim", bodies[i], now=now[0])
    assert lim.check_and_consume("ali", "hello", now=now[0]).allowed
