"""No-match closure: never a dead end, and never a silent one."""

from datetime import datetime

from nearmind.agent import Agent
from nearmind.config import Settings
from nearmind.llm import FakeModel
from nearmind.models import Availability, InventoryItem
from nearmind.world import World


def _world(**kw) -> World:
    w = World.sandbox(Settings(start_time=datetime(2026, 11, 14, 19, 0)), **kw)
    w.reply_script = {}
    return w


def test_nobody_has_it_offers_local_alternatives():
    w = _world()
    result = Agent(w, FakeModel()).handle("anyone have a whisk?")
    assert result.request.status.value == "no_match"
    assert result.closure
    assert "whisk" in result.closure
    assert any(l.action.value == "no_match" for l in w.logs)


def test_baking_soda_at_night_names_substitutes():
    w = World.sandbox(Settings(start_time=datetime(2026, 11, 14, 2, 0)))
    w.reply_script = {}
    result = Agent(w, FakeModel()).handle("anyone have baking soda? making a cake")
    assert result.request.status.value == "no_match"
    assert "Nobody is awake with baking soda" in result.closure
    assert "white vinegar" in result.closure or "lemon juice" in result.closure


def test_only_holder_out_closes_with_reason():
    w = _world()
    w.neighbours["karim"].inventory = [InventoryItem(item="whisk", quantity=1)]
    for nid in w.neighbours:
        if nid != "karim":
            w.neighbours[nid].inventory = []
    w.set_availability("karim", Availability.NOT_AT_HOME, "Away until Sunday")

    result = Agent(w, FakeModel()).handle("anyone have a whisk?")
    assert result.request.status.value == "no_match"
    assert "is out" in result.closure
    assert "Karim" in result.closure
    assert "Away until Sunday" in result.closure
    assert w.stats["no_match"] == 1


def test_closure_is_logged_with_the_same_reasoning():
    w = _world()
    result = Agent(w, FakeModel()).handle("anyone have a whisk?")
    entry = [l for l in w.logs if l.action.value == "no_match"][0]
    assert result.closure == entry.entities["closure"]
    assert entry.reason.startswith("No usable match")
