"""Urgency override: the paired 02:00 contrast.

Low urgency respects sleep. High/emergency wakes a neighbour *deliberately*,
and the log records that as an override — not as an incidental success.
"""

from datetime import datetime

from nearmind.agent import Agent
from nearmind.availability_probe import contacted_ids
from nearmind.config import Settings
from nearmind.llm import FakeModel
from nearmind.world import World


def _night() -> World:
    world = World.sandbox(Settings(start_time=datetime(2026, 11, 14, 2, 5)))
    world.reply_script = {}
    return world


def test_low_urgency_at_2am_wakes_nobody():
    world = _night()
    result = Agent(world, FakeModel()).handle("anyone have salt? i want some for dinner")

    assert contacted_ids(world, result.request.id) == set()
    assert not result.offers
    assert world.stats["wakes"] == 0
    assert result.request.status.value == "no_match"
    # Every skip is explained with the clock and the window.
    skips = [l for l in world.logs if l.action.value == "skipped_neighbour"]
    assert len(skips) == 3
    assert all("sleep window" in s.reason and "02:05" in s.reason for s in skips)


def test_high_urgency_at_2am_wakes_deliberately():
    world = _night()
    result = Agent(world, FakeModel()).handle(
        "URGENT my pipe is leaking badly, does anyone have a drill or tools"
    )

    contacted = contacted_ids(world, result.request.id)
    assert "karim" in contacted, "the holder must be reached"
    assert world.stats["wakes"] >= 1
    overrides = [l for l in world.logs if l.action.value == "urgency_override"]
    assert overrides, "the wake must be logged as an override"
    assert "deliberately" in overrides[0].reason.lower()
    assert result.offers


def test_override_only_fires_when_someone_is_actually_asleep():
    world = World.sandbox(Settings(start_time=datetime(2026, 11, 14, 19, 0)))
    world.reply_script = {}
    Agent(world, FakeModel()).handle("URGENT leak! anyone have a drill?")
    assert world.stats["wakes"] == 0
    assert not [l for l in world.logs if l.action.value == "urgency_override"]


def test_urgency_levels_are_distinct():
    from nearmind.llm import FakeModel as FM
    import json

    m = FM()
    low = json.loads(m.parse_intent("anyone have salt"))
    high = json.loads(m.parse_intent("need salt right now"))
    emergency = json.loads(m.parse_intent("emergency! the pipe is leaking, anyone have a drill?"))
    assert low["urgency"] == "low"
    assert high["urgency"] == "high"
    assert emergency["urgency"] == "emergency"
