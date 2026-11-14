"""Safety veto — must hold under scarcity.

Includes the required proof that the veto test *can* fail: with the veto rule
removed, a creaky ladder becomes recommendable and the test goes red.
"""

import pytest

from nearmind import safety
from nearmind.agent import Agent
from nearmind.config import Settings
from nearmind.llm import FakeModel
from nearmind.models import SafetyStatus
from nearmind.world import World
from datetime import datetime


def _ladder_world() -> World:
    """The only ladders in the building are unsafe. No substitute exists."""
    world = World.sandbox(Settings(start_time=datetime(2026, 11, 14, 19, 0)))
    world.reply_script = {}
    # Remove Ali's good step ladder: scarcity is the whole point.
    world.neighbours["ali"].inventory = [
        inv for inv in world.neighbours["ali"].inventory if "ladder" not in inv.item
    ]
    return world


def test_only_unsafe_ladders_exist(world=None):
    w = _ladder_world()
    holders = [nid for nid in w.neighbours if any("ladder" in i.item for i in w.neighbours[nid].inventory)]
    assert holders, "the scenario must actually have ladders in it"


def test_creaky_ladder_is_vetoed_and_never_offered():
    w = _ladder_world()
    result = Agent(w, FakeModel()).handle("I need a ladder for my smoke detector, mine broke")

    assert result.offers == [], "no offer may survive an unsafe ladder"
    assert result.recommendation is None
    vetoes = [l for l in w.logs if l.action.value == "safety_veto"]
    assert vetoes, "the veto must be logged"
    assert any("creaky" in l.reason for l in vetoes)
    assert result.request.status.value == "no_match"


def test_veto_holds_even_when_it_is_the_only_ladder():
    """Scarcity pressure: exactly one ladder, and it is creaky."""
    w = World.sandbox(Settings(start_time=datetime(2026, 11, 14, 19, 0)))
    w.reply_script = {}
    for nid in w.neighbours:
        w.neighbours[nid].inventory = [
            inv for inv in w.neighbours[nid].inventory if "ladder" not in inv.item
        ]
    from nearmind.models import InventoryItem

    w.neighbours["karim"].inventory.append(
        InventoryItem(item="ladder", condition="creaky", attributes={"stability": "creaky"})
    )

    result = Agent(w, FakeModel()).handle("anyone have a ladder? I need one")
    assert result.offers == []
    vetoes = [l for l in w.logs if l.action.value == "safety_veto"]
    assert len(vetoes) == 1
    assert "creaky" in vetoes[0].reason


def test_veto_survives_a_model_that_says_safe():
    """Defence in depth: the deterministic rules tighten, never loosen."""
    verdict = safety.tighten(
        "ladder",
        "creaky",
        {"stability": "creaky"},
        safety_model_says_safe(),
    )
    assert verdict.status is SafetyStatus.UNSAFE
    assert any("creaky" in h for h in verdict.hazards)
    assert "not safe" in verdict.reason.lower()


def test_a_good_ladder_passes():
    w = World.sandbox(Settings(start_time=datetime(2026, 11, 14, 19, 0)))
    w.reply_script = {}
    result = Agent(w, FakeModel()).handle("I need a ladder for my smoke detector")
    assert result.offers, "the safe step ladder should be offered"
    assert all(o.safety.status is SafetyStatus.SAFE for o in result.offers)
    assert all(o.item != "ladder" or o.condition != "creaky" for o in result.offers)


# --------------------------------------------------------------------------- #
# Can-fail proof
# --------------------------------------------------------------------------- #


def test_veto_test_fails_when_veto_removed(monkeypatch):
    """If `tighten` stopped vetoing, the creaky ladder would be offered.

    We assert the *inverse* here: with the rules neutered, an offer appears.
    That is what proves the earlier assertions are load-bearing rather than
    vacuous.
    """
    from nearmind.models import SafetyVerdict

    def neutered(item, condition, attributes, verdict):
        return SafetyVerdict(status=SafetyStatus.SAFE, reason="(rules disabled for can-fail proof)")

    monkeypatch.setattr(safety, "tighten", neutered)
    monkeypatch.setattr("nearmind.agent.safety.tighten", neutered)

    w = _ladder_world()
    result = Agent(w, FakeModel()).handle("I need a ladder for my smoke detector, mine broke")

    assert result.offers, "with the veto removed an unsafe ladder is offered — the test can fail"
    assert any(o.item == "ladder" and o.condition == "creaky" for o in result.offers)


def safety_model_says_safe():
    from nearmind.models import SafetyVerdict

    return SafetyVerdict(status=SafetyStatus.SAFE, reason="Looks fine to me.")
