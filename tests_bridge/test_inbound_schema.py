"""Unparseable inbound must degrade gracefully and never corrupt state."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from bridge.events import (
    InboundEvent,
    InboundKind,
    ContactRef,
    ValidationFailure,
    validate_inbound,
)

T = datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc)
INDEX = {
    "111@s.whatsapp.net": ContactRef("karim", "Karim"),
    "222@s.whatsapp.net": ContactRef("ali", "Ali"),
}


def good(**over):
    base = {
        "id": "m1",
        "sender": "111@s.whatsapp.net",
        "timestamp": T.isoformat(),
        "content": "got the pink stuff",
    }
    base.update(over)
    return base


def v(payload, **kw):
    return validate_inbound(payload, contact_index=INDEX, now=T + timedelta(seconds=5), **kw)


def test_valid_text_is_an_event():
    ev = v(good())
    assert isinstance(ev, InboundEvent)
    assert ev.kind is InboundKind.TEXT
    assert ev.sender.contact_id == "karim"
    assert ev.body == "got the pink stuff"
    assert ev.command is None


def test_command_is_classified_as_control():
    ev = v(good(content=" STOP "))
    assert ev.kind is InboundKind.COMMAND
    assert ev.command.kind.value == "stop"
    assert ev.is_control_command


def test_media_without_caption_is_media_event():
    ev = v(good(content="", media_type="image"))
    assert ev.kind is InboundKind.MEDIA
    assert ev.media_label == "image"


def test_caption_beats_media():
    ev = v(good(content="is this the right one?", media_type="image"))
    assert ev.kind is InboundKind.TEXT


def test_reaction_is_ignored_by_flow():
    ev = v(good(content="", is_reaction=True))
    assert ev.kind is InboundKind.REACTION


# --- every malformed shape becomes a ValidationFailure, never an exception --


@pytest.mark.parametrize(
    "payload,reason",
    [
        (None, "not_mapping"),
        ("a string", "not_mapping"),
        (42, "not_mapping"),
        ([], "not_mapping"),
        ({}, "missing_sender"),
        ({"sender": 111, "id": "x"}, "missing_sender"),
        ({"sender": "", "id": "x"}, "missing_sender"),
        ({"sender": "111@s.whatsapp.net"}, "missing_message_id"),
        ({"sender": "111@s.whatsapp.net", "id": ""}, "missing_message_id"),
        ({"sender": "111@s.whatsapp.net", "id": "x"}, "bad_timestamp"),
        ({"sender": "111@s.whatsapp.net", "id": "x", "timestamp": "not a date"}, "bad_timestamp"),
        ({"sender": "111@s.whatsapp.net", "id": "x", "is_from_me": True}, "from_self"),
        ({"sender": "999@s.whatsapp.net", "id": "x"}, "missing_sender"),
        ({"sender": "123@g.us", "id": "x", "timestamp": T.isoformat()}, "group_chat"),
    ],
)
def test_malformed_payloads_fail_cleanly(payload, reason):
    out = v(payload)
    assert isinstance(out, ValidationFailure), out
    assert out.reason == reason


def test_unknown_sender_cannot_issue_stop():
    """A stranger's STOP must not take a neighbour offline."""
    out = v({"sender": "999@s.whatsapp.net", "id": "x", "timestamp": T.isoformat(), "content": "STOP"})
    assert isinstance(out, ValidationFailure)
    assert out.reason == "missing_sender"


def test_stale_message_is_rejected_as_replay():
    old = (T - timedelta(hours=9)).isoformat()
    out = v({"sender": "111@s.whatsapp.net", "id": "x", "timestamp": old, "content": "STOP"},
            max_age_seconds=6 * 3600)
    assert isinstance(out, ValidationFailure)
    assert out.reason == "unsupported_type"


def test_enormous_body_fails_rather_than_truncates_silently():
    out = v(good(content="x" * 2_000_000))
    assert isinstance(out, ValidationFailure)
    assert out.reason == "too_large"


def test_long_but_sane_body_is_capped_and_marked():
    ev = v(good(content="a" * 10_000))
    assert isinstance(ev, InboundEvent)
    assert len(ev.body) <= 4_001
    assert ev.body.endswith("\u2026")


def test_control_and_zero_width_chars_are_stripped():
    ev = v(good(content="\u200bgo\u200bod\x00\x07 yes\u200b"))
    assert isinstance(ev, InboundEvent)
    assert ev.body == "good yes"


def test_epoch_seconds_timestamp_accepted():
    ms = int(T.timestamp())
    ev = v({"sender": "111@s.whatsapp.net", "id": "x", "timestamp": ms, "content": "hi"})
    assert isinstance(ev, InboundEvent)
    assert ev.received_at.year == 2026


def test_numeric_content_is_coerced_not_crashed():
    ev = v(good(content=5))
    assert isinstance(ev, InboundEvent)
    assert ev.body == "5"


def test_event_requires_command_for_command_kind():
    with pytest.raises(ValueError):
        InboundEvent(kind=InboundKind.COMMAND, sender=ContactRef("k", "K"), received_at=T,
                     message_id="m", body="stop")


def test_contact_ref_rejects_phone_like_id():
    with pytest.raises(ValueError):
        ContactRef("316123456789012", "Someone")
