"""The availability state machine: STOP sticky, BUSY expiring, both idempotent."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from bridge.availability import (
    AvailabilityState,
    AvailabilityStore,
)
from bridge.commands import CommandKind, ParsedCommand


def stop() -> ParsedCommand:
    return ParsedCommand(CommandKind.STOP, "stop")


def busy(seconds=1800) -> ParsedCommand:
    return ParsedCommand(CommandKind.BUSY, "busy", seconds)


def resume() -> ParsedCommand:
    return ParsedCommand(CommandKind.RESUME, "resume")


T = datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc)


@pytest.fixture()
def store() -> AvailabilityStore:
    return AvailabilityStore(default_busy_seconds=3600, max_busy_seconds=12 * 3600)


def test_unknown_contact_is_available(store):
    assert store.ensure("karim", T).state is AvailabilityState.AVAILABLE


def test_stop_is_sticky_and_survives_arbitrary_time(store):
    store.apply_command("karim", stop(), now=T)
    far = T + timedelta(days=30)
    av = store.ensure("karim", far)
    assert av.state is AvailabilityState.NOT_AT_HOME
    assert av.is_stopped
    assert av.expires_at is None
    allowed, reason = store.may_contact("karim", now=far)
    assert not allowed and "STOP" in reason


def test_stop_is_idempotent_and_keeps_original_since(store):
    first = store.apply_command("karim", stop(), now=T)
    assert first.changed
    later = T + timedelta(hours=3)
    second = store.apply_command("karim", stop(), now=later)
    assert second.changed is False
    assert second.after.since == first.after.since == T
    assert second.note == "already stopped"


def test_stop_overrides_busy(store):
    store.apply_command("karim", busy(7200), now=T)
    tr = store.apply_command("karim", stop(), now=T + timedelta(minutes=5))
    assert tr.changed
    assert tr.after.is_stopped
    assert tr.after.expires_at is None
    # advancing past the old busy window must NOT make them available again
    after_busy = store.ensure("karim", T + timedelta(hours=3))
    assert after_busy.state is AvailabilityState.NOT_AT_HOME


def test_busy_while_busy_extends_window(store):
    store.apply_command("karim", busy(600), now=T)
    store.apply_command("karim", busy(3600), now=T + timedelta(minutes=2))
    av = store.ensure("karim", T + timedelta(minutes=2))
    assert av.state is AvailabilityState.BUSY
    assert av.expires_at == T + timedelta(minutes=62)


def test_busy_expires_on_its_own(store):
    store.apply_command("karim", busy(1800), now=T)
    assert store.ensure("karim", T + timedelta(minutes=29)).state is AvailabilityState.BUSY
    assert store.ensure("karim", T + timedelta(minutes=30)).state is AvailabilityState.AVAILABLE
    # idempotent: sweeping again does nothing
    assert store.expire_due(T + timedelta(hours=1)) == []


def test_busy_expiry_reported_once_by_sweep(store):
    store.apply_command("karim", busy(60), now=T)
    results = store.expire_due(T + timedelta(seconds=61))
    assert len(results) == 1
    assert results[0].contact_id == "karim"
    assert results[0].after.state is AvailabilityState.AVAILABLE


def test_resume_lifts_stop(store):
    store.apply_command("karim", stop(), now=T)
    tr = store.apply_command("karim", resume(), now=T + timedelta(hours=1))
    assert tr.changed
    assert tr.after.state is AvailabilityState.AVAILABLE
    assert not tr.after.is_stopped
    assert store.may_contact("karim", now=T + timedelta(hours=1))[0]


def test_resume_when_available_is_noop(store):
    tr = store.apply_command("karim", resume(), now=T)
    assert tr.changed is False


def test_timed_stop_expires(store):
    cmd = ParsedCommand(CommandKind.STOP, "stop", 3600)
    store.apply_command("karim", cmd, now=T)
    av = store.ensure("karim", T + timedelta(minutes=30))
    assert av.is_stopped and av.expires_at == T + timedelta(hours=1)
    after = store.ensure("karim", T + timedelta(hours=1, seconds=1))
    assert after.state is AvailabilityState.AVAILABLE
    assert not after.is_stopped


def test_help_does_not_change_state(store):
    tr = store.apply_command("karim", ParsedCommand(CommandKind.HELP, "help"), now=T)
    assert tr.changed is False
    assert tr.after.state is AvailabilityState.AVAILABLE


def test_out_of_building_cannot_be_reached(store):
    store.set_sandbox_state(
        "ali", AvailabilityState.NOT_AT_HOME, reason="at the gym", now=T
    )
    allowed, reason = store.may_contact("ali", now=T)
    assert not allowed and "not at home" in reason


def test_asleep_is_not_reachable_even_when_available(store):
    allowed, reason = store.may_contact("ali", now=T, asleep=True)
    assert not allowed and "asleep" in reason


def test_sandbox_cannot_override_a_real_stop(store):
    store.apply_command("karim", stop(), now=T)
    tr = store.set_sandbox_state("karim", AvailabilityState.AVAILABLE, reason="scenario", now=T)
    assert tr.changed is False
    assert "ignored" in (tr.note or "")
    assert store.ensure("karim", T).is_stopped


def test_snapshot_matches_ui_contract(store):
    store.apply_command("karim", busy(1800), now=T)
    snap = store.snapshot("karim", T)
    assert snap["state"] == "busy"
    assert snap["source"] == "whatsapp_busy"
    assert snap["reason"]
    assert snap["since"] == T.isoformat()
    assert snap["expires_at"]


def test_busy_cannot_weaken_a_sticky_stop(store):
    """Regression: BUSY after STOP must not cancel it or let it expire."""
    store.apply_command("karim", stop(), now=T)
    tr = store.apply_command("karim", busy(600), now=T + timedelta(minutes=1))
    assert tr.changed is False
    assert tr.after.is_stopped
    far = store.ensure("karim", T + timedelta(hours=5))
    assert far.state is AvailabilityState.NOT_AT_HOME and far.is_stopped
