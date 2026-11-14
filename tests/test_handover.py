"""Handover state machine and expiry.

The requirement is behavioural, not structural: after a neighbour says
'give me 5' and goes quiet, NearMind must do something useful on its own.
"""

from datetime import datetime

import pytest

from nearmind.agent import Agent
from nearmind.config import Settings
from nearmind.handover import InvalidTransition, agree, collect, open_handover, release, sweep
from nearmind.llm import FakeModel
from nearmind.models import HandoverState, InventoryItem, OfferStatus
from nearmind.world import World

T0 = datetime(2026, 11, 14, 19, 0)


def _world() -> World:
    w = World.sandbox(Settings(start_time=T0))
    w.reply_script = {}
    return w


def _choose(world: World, neighbour_id: str = "karim"):
    agent = Agent(world, FakeModel())
    result = agent.handle("anyone have salt?")
    offer = next(o for o in result.offers if o.neighbour_id == neighbour_id)
    return agent, result, agent.choose(result.request.id, offer.id)


def test_expiry_is_within_the_required_window():
    w = _world()
    _, _, payload = _choose(w)
    handover = w.handovers[payload["handover"]["id"]]
    minutes = (handover.expires_at - handover.created_at).total_seconds() / 60
    assert 15 <= minutes <= 30


def test_choose_releases_others_but_keeps_a_standby():
    w = _world()
    w.neighbours["ali"].inventory.append(InventoryItem(item="salt", quantity=0.5, unit="kg"))
    agent, result, payload = _choose(w)
    assert payload["released"], "the other neighbour must be released"
    released_ids = {r["neighbour_id"] for r in payload["released"]}
    assert "ali" in released_ids
    # The runner-up is kept on standby, explicitly.
    standby = [r for r in payload["released"] if r.get("standby")]
    assert standby, "second-best must stay available for pivot"
    assert any("standby" in l.reason or "standby" in l.reason for l in w.logs)


def test_expiry_checks_back_then_pivots():
    w = _world()
    w.neighbours["ali"].inventory.append(InventoryItem(item="salt", quantity=0.5, unit="kg"))
    agent, result, payload = _choose(w, "karim")
    handover = w.handovers[payload["handover"]["id"]]

    w.tick(21)
    first = sweep(w)
    assert first and first[0]["action"] == "checked_back"
    assert handover.checked_back_at is not None
    assert handover.state is HandoverState.PROPOSED
    # The check-back actually puts a message in the thread.
    thread = next(t for t in w.threads_for(result.request.id) if t.neighbour_id == "karim")
    assert any("checking" in m.text for m in thread.messages)

    w.tick(31)
    second = sweep(w)
    assert second and second[0]["action"] == "pivoted"
    assert second[0]["to_neighbour"] == "ali"
    assert handover.state is HandoverState.EXPIRED
    assert result.request.status.value == "awaiting_choice"
    assert any(l.action.value == "handover_pivoted" for l in w.logs)


def test_expiry_with_no_alternative_closes_honestly():
    w = _world()
    agent, result, payload = _choose(w)
    w.tick(21)
    sweep(w)
    w.tick(31)
    outcomes = sweep(w)
    assert outcomes[0]["action"] == "closed"
    assert result.request.status.value == "no_match"
    assert "didn't come back" in result.request.closure


def test_legal_transitions_and_ledger_on_completion():
    w = _world()
    agent, result, payload = _choose(w)
    handover = w.handovers[payload["handover"]["id"]]

    agent.finish_handover(handover.id)
    assert handover.state is HandoverState.RELEASED
    assert result.request.status.value == "fulfilled"
    assert len(w.ledger) == 1
    assert w.ledger[0].neighbour_id == "karim"
    assert w.ledger[0].direction.value == "maryam_owes"
    assert w.stats["fulfilled"] == 1


def test_illegal_transition_is_rejected():
    w = _world()
    _, _, payload = _choose(w)
    handover = w.handovers[payload["handover"]["id"]]
    release(w, handover)
    with pytest.raises(InvalidTransition):
        collect(w, handover)


def test_vetoed_offer_cannot_be_chosen():
    w = World.sandbox(Settings(start_time=T0))
    w.reply_script = {}
    for nid in w.neighbours:
        w.neighbours[nid].inventory = [
            i for i in w.neighbours[nid].inventory if "ladder" not in i.item
        ]
    from nearmind.models import InventoryItem

    w.neighbours["karim"].inventory.append(
        InventoryItem(item="ladder", condition="creaky", attributes={"stability": "creaky"})
    )
    agent = Agent(w, FakeModel())
    result = agent.handle("anyone have a ladder?")
    assert not result.offers  # nothing to choose; the API enforces the same thing


def test_complete_works_after_an_explicit_agree():
    """Regression: agreeing then completing must not raise 'agreed → agreed'."""
    w = _world()
    agent, result, payload = _choose(w)
    handover = w.handovers[payload["handover"]["id"]]
    agree(w, handover)
    agent.finish_handover(handover.id)
    assert handover.state is HandoverState.RELEASED
    assert len(w.ledger) == 1
