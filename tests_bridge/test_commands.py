"""STOP / BUSY / RESUME parsing must be instant, obvious and unbreakable."""

from __future__ import annotations

import pytest

from bridge.commands import CommandKind, parse_command


@pytest.mark.parametrize(
    "text",
    ["STOP", "stop", "  Stop.  ", "stop!!", "STOP!", "Stop\n", "stop stop",
     "don't message me", "DON'T MSG ME", "unsubscribe", "leave me alone",
     "no thanks", "Stop.", "sToP"],
)
def test_stop_is_recognised_however_typed(text):
    cmd = parse_command(text)
    assert cmd is not None, text
    assert cmd.kind is CommandKind.STOP


@pytest.mark.parametrize(
    "text,seconds",
    [("busy", 3600), ("BUSY", 3600), ("Busy.", 3600), ("busy 30m", 1800),
     ("busy for 2 hours", 7200), ("brb 10 min", 600), ("busy 1h", 3600),
     ("Busy 45 minutes", 2700)],
)
def test_busy_with_and_without_window(text, seconds):
    cmd = parse_command(text)
    assert cmd is not None, text
    assert cmd.kind is CommandKind.BUSY
    assert cmd.duration_seconds == seconds


def test_busy_window_is_clamped_to_a_sane_maximum():
    cmd = parse_command("busy 400h")
    assert cmd is not None and cmd.kind is CommandKind.BUSY
    assert cmd.duration_seconds == 12 * 3600


def test_timed_stop_is_a_stop_with_an_expiry():
    cmd = parse_command("stop 2h")
    assert cmd is not None
    assert cmd.kind is CommandKind.STOP
    assert cmd.duration_seconds == 7200


@pytest.mark.parametrize("text", ["resume", "RESUME", "unstop", "unblock", "start", "im back", "I am back"])
def test_resume(text):
    cmd = parse_command(text)
    assert cmd is not None and cmd.kind is CommandKind.RESUME


@pytest.mark.parametrize("text", ["help", "commands", "?"])
def test_help(text):
    cmd = parse_command(text)
    assert cmd is not None and cmd.kind is CommandKind.HELP


@pytest.mark.parametrize(
    "text",
    [None, "", "   ", "\n\t", 123, [], {"a": 1},
     "the salt is in the back cupboard", "I'll bring the ladder back",
     "stop by anytime", "yes the pink stuff is baking soda",
     "busy street out here lol", "can you stop at the shop",
     "got the pink stuff", "\u200b", "x" * 200],
)
def test_non_commands_are_not_commands(text):
    assert parse_command(text) is None, text


def test_parse_never_raises_and_is_idempotent_on_canonical():
    """Parsing a canonical verb back must yield the same kind — this is what
    makes repeated STOP/BUSY harmless downstream."""
    for text in ["STOP", "busy", "busy 30m", "resume"]:
        cmd = parse_command(text)
        assert cmd is not None
        again = parse_command(cmd.canonical)
        assert again is not None and again.kind is cmd.kind


def test_long_line_but_clean_first_line_is_a_command():
    assert parse_command("STOP\n(and nothing after 10pm please)").kind is CommandKind.STOP
