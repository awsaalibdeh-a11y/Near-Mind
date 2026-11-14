"""End-to-end against the fake transport: no real send, real behaviour.

Each test drives the bridge exactly as the Flask backend would —
``receive()`` then ``send()`` — and asserts the observable result in the fake
transport's outbox plus the availability/limiter state.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from bridge.config import BridgeConfig
from bridge.core import WhatsAppBridge
from bridge.events import SendOutcome, InboundKind
from bridge.transport import FakeTransport, TransportError

from .conftest import CONTACTS, WIRE, Clock


def deliver(bridge, transport, contact_id, text, clock, **kw):
    transport.deliver(WIRE[contact_id], text, at=clock(), **kw)
    return bridge.receive(now=clock())


# --- the core promise: STOP is absolute ------------------------------------


def test_stop_silences_every_future_send(bridge, transport, clock):
    batch = deliver(bridge, transport, "karim", "  STOP!!  ", clock)
    assert len(batch.events) == 1
    assert batch.events[0].kind is InboundKind.COMMAND

    # One acknowledgement is owed — and it is sent.
    acks = transport.sent_to("karim")
    assert len(acks) == 1 and "STOP" in acks[0].body

    # Every subsequent send is suppressed, including "urgent".
    clock.advance(hours=1)
    for body, urgent in [("did you find the ladder?", False), ("EMERGENCY water leak", True)]:
        r = bridge.send("karim", body, urgent=urgent, now=clock())
        assert r.outcome is SendOutcome.SUPPRESSED
        assert r.reason == "stopped"
    assert len(transport.sent_to("karim")) == 1


def test_stop_survives_across_days_and_restarts_of_polls(bridge, transport, clock):
    deliver(bridge, transport, "ali", "stop", clock)
    for _ in range(5):
        clock.advance(days=3)
        batch = bridge.receive(now=clock())
        assert batch.events == ()
        assert bridge.send("ali", "hi", now=clock()).outcome is SendOutcome.SUPPRESSED


def test_resume_lifts_stop_and_messaging_works_again(bridge, transport, clock):
    deliver(bridge, transport, "ali", "STOP", clock)
    clock.advance(minutes=10)
    deliver(bridge, transport, "ali", "resume", clock)
    r = bridge.send("ali", "Thanks! Ladder still needed?", now=clock())
    assert r.outcome is SendOutcome.SENT



def test_stop_while_busy_still_applies(bridge, transport, clock):
    deliver(bridge, transport, "karim", "busy 2h", clock)
    clock.advance(minutes=5)
    deliver(bridge, transport, "karim", "stop", clock)
    av = bridge.availability.ensure("karim", clock())
    assert av.is_stopped
    clock.advance(hours=3)  # past the old busy window
    assert bridge.send("karim", "x", now=clock()).reason == "stopped"


def test_busy_after_stop_keeps_the_person_stopped(bridge, transport, clock):
    deliver(bridge, transport, "karim", "STOP", clock)
    clock.advance(minutes=2)
    deliver(bridge, transport, "karim", "busy 30m", clock)
    last = transport.sent_to("karim")[-1]
    assert "still set to STOP" in last.body
    clock.advance(hours=2)  # past the busy window
    assert bridge.send("karim", "x", now=clock()).reason == "stopped"


# --- BUSY is a window -------------------------------------------------------


def test_busy_expires_and_then_sends_are_allowed(bridge, transport, clock):
    deliver(bridge, transport, "karim", "busy 30m", clock)
    ack = transport.sent_to("karim")[-1]
    assert "30 min" in ack.body

    r = bridge.send("karim", "quick question", now=clock())
    assert r.outcome is SendOutcome.SUPPRESSED and r.reason == "busy"

    clock.advance(minutes=31)
    bridge.receive(now=clock())  # sweep
    r = bridge.send("karim", "quick question", now=clock())
    assert r.outcome is SendOutcome.SENT


def test_urgent_overrides_busy_but_not_stop(bridge, transport, clock):
    deliver(bridge, transport, "karim", "busy", clock)
    r = bridge.send("karim", "Water is coming through my ceiling", urgent=True, now=clock())
    assert r.outcome is SendOutcome.SENT


# --- out of building --------------------------------------------------------


def test_not_at_home_is_never_reached_even_urgently(bridge, transport, clock):
    from bridge.availability import AvailabilityState

    bridge.availability.set_sandbox_state(
        "umm_samir", AvailabilityState.NOT_AT_HOME, reason="visiting her sister", now=clock()
    )
    r = bridge.send("umm_samir", "any baking soda?", urgent=True, now=clock())
    assert r.outcome is SendOutcome.SUPPRESSED and r.reason == "not_at_home"


# --- rate limiting through the facade --------------------------------------


def test_burst_limit_through_the_bridge(bridge, transport, clock):
    """Four messages in one burst, each answered, then the fifth is refused."""
    allowed, blocked = 0, 0
    for i in range(5):
        r = bridge.send("karim", f"msg {i}", now=clock())
        if r.outcome is SendOutcome.SENT:
            allowed += 1
            # a reply keeps the thread alive so backoff is not the limiter hit
            deliver(bridge, transport, "karim", f"yes {i}", clock)
        else:
            blocked += 1
            assert r.outcome is SendOutcome.REFUSED
            assert r.reason == "burst"
    assert allowed == 4 and blocked == 1


def test_ack_is_exempt_from_rate_limit(bridge, transport, clock):
    for i in range(4):
        assert bridge.send("karim", f"m{i}", now=clock()).delivered
        deliver(bridge, transport, "karim", f"r{i}", clock)
    # bucket exhausted, but a command ack must still go out
    deliver(bridge, transport, "karim", "busy 15m", clock)
    bodies = [r.body for r in transport.sent_to("karim")]
    assert any("15 min" in b for b in bodies)


# --- malformed inbound does not corrupt the bridge -------------------------


def test_malformed_inbound_is_separated_from_events(bridge, transport, clock):
    transport.deliver(WIRE["karim"], "hello", at=clock(), message_id="ok-1")
    # A group message (not ours), a self echo, and an unknown sender.
    transport.deliver("999999@g.us", "lol", at=clock(), is_group=True)
    transport._inbox.append(
        type(transport._inbox[0])(
            message_id="self-1", sender_key="me", timestamp=clock(),
            content="nearmind out", is_from_me=True,
        )
    )
    transport.deliver("777@s.whatsapp.net", "STOP", at=clock())
    batch = bridge.receive(now=clock())
    assert len(batch.events) == 1
    assert batch.events[0].body == "hello"
    assert len(batch.failures) == 2  # self + unknown (group filtered by validate too)
    # The stranger's STOP changed nothing.
    assert bridge.send("karim", "next", now=clock()).delivered


def test_garbage_payload_from_a_transport_does_not_raise(bridge, transport, clock):
    class Garbage:
        def as_payload(self):
            return None

    transport._inbox.append(Garbage())  # type: ignore[arg-type]
    batch = bridge.receive(now=clock())
    assert len(batch.failures) == 1
    assert bridge.send("ali", "still works", now=clock()).delivered


def test_transport_failure_becomes_failed_receipt():
    class Broken(FakeTransport):
        def send_text(self, key, body):
            raise TransportError("server down")

    clock = Clock()
    b = WhatsAppBridge(contacts=CONTACTS, transport=Broken(WIRE, clock=clock), clock=clock)
    r = b.send("karim", "hello", now=clock())
    assert r.outcome is SendOutcome.FAILED and r.reason == "transport_error"
    assert b.report().failed_total == 1


# --- duplicate ping and silence -------------------------------------------


def test_identical_message_is_not_repeated(bridge, transport, clock):
    assert bridge.send("ali", "Any salt?", now=clock()).delivered
    r = bridge.send("ali", "Any salt?", now=clock())
    assert r.outcome is SendOutcome.REFUSED and r.reason == "duplicate"


def test_ghosted_thread_backs_off(bridge, transport, clock):
    assert bridge.send("ali", "Any salt?", now=clock()).delivered
    clock.advance(seconds=61)
    # no reply -> second message also allowed (below the backoff threshold)
    assert bridge.send("ali", "Salt? Really need it", now=clock()).delivered
    clock.advance(seconds=61)
    r = bridge.send("ali", "third ping", now=clock())
    assert r.outcome is SendOutcome.REFUSED
    assert r.reason == "silence_backoff"


# --- housekeeping ----------------------------------------------------------


def test_receive_is_idempotent_for_the_same_message(bridge, transport, clock):
    transport.deliver(WIRE["karim"], "hello", at=clock(), message_id="dup-me")
    first = bridge.receive(now=clock())
    second = bridge.receive(now=clock())
    assert len(first.events) == 1
    assert second.events == ()


def test_replay_window_excludes_old_backlog_on_first_poll(clock, transport):
    old = clock() - timedelta(hours=10)
    transport.deliver(WIRE["karim"], "STOP", at=old, message_id="ancient")
    b = WhatsAppBridge(contacts=CONTACTS, transport=transport, clock=clock)
    batch = b.receive(now=clock())
    assert batch.events == ()
    assert not b.availability.ensure("karim", clock()).is_stopped


def test_report_is_honest_about_mode_and_transport(bridge):
    rep = bridge.report()
    assert rep.mode == "dry_run"
    assert rep.transport == "fake"
    assert rep.sandbox is True
    assert set(rep.guards) == {"karim", "ali", "umm_samir"}


def test_live_mode_refuses_without_an_explicit_transport(clock):
    cfg = BridgeConfig(dry_run=False, allow_live_sends=True)
    with pytest.raises(ValueError):
        WhatsAppBridge(config=cfg, contacts=CONTACTS, clock=clock)


def test_dry_run_mode_ignores_a_real_looking_transport(clock):
    """Even if someone wires the MCP transport, dry_run replaces it."""

    class PretendReal(FakeTransport):
        is_fake = False

    cfg = BridgeConfig(dry_run=True, allow_live_sends=False)
    b = WhatsAppBridge(config=cfg, transport=PretendReal(WIRE, clock=clock), contacts=CONTACTS, clock=clock)
    assert b.is_fake_transport is True
    assert b.mode == "dry_run"


def test_allow_live_without_flipping_dry_run_still_dry(clock):
    cfg = BridgeConfig(dry_run=True, allow_live_sends=True)
    assert cfg.effective_dry_run() is True
    cfg2 = BridgeConfig(dry_run=False, allow_live_sends=False)
    assert cfg2.effective_dry_run() is True
