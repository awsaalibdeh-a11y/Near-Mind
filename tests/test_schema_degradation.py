"""Schema failure degrades gracefully and never corrupts state.

Every model call is schema-validated. These tests drive the flow with a model
that returns prose, empty strings, arrays, and plausible-but-invalid objects,
then assert that:

* state that matters (ledger, inventory, stats) is unchanged or explicitly
  conservative;
* the failure is logged with a reason;
* the flow still produces something a user can act on.
"""

from copy import deepcopy
from datetime import datetime

import pytest

from nearmind.agent import Agent
from nearmind.config import Settings
from nearmind.llm import FailingModel, FakeModel
from nearmind.schemas import (
    IntentSchema,
    ReplySchema,
    SafetySchema,
    StyleSchema,
    validate_payload,
)
from nearmind.world import World

T0 = datetime(2026, 11, 14, 19, 0)


def _world() -> World:
    w = World.sandbox(Settings(start_time=T0))
    w.reply_script = {}
    return w


# --------------------------------------------------------------------------- #
# The validator itself
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "payload",
    ["", "yeah i think so?? lol", "not json at all", "[1,2,3]", '{"quantity": -5}', None],
)
def test_garbage_never_validates(payload):
    outcome = validate_payload(IntentSchema, payload)
    assert outcome.ok is False
    assert outcome.error


def test_fenced_json_is_accepted():
    raw = 'Here you go:\n```json\n{"item": "salt", "quantity": 2}\n```'
    outcome = validate_payload(IntentSchema, raw)
    assert outcome.ok
    assert outcome.model.item == "salt"
    assert outcome.model.quantity == 2


def test_scalar_string_quantity_is_accepted_without_inventing_anything():
    raw = '{"item": "salt", "quantity": "2"}'
    outcome = validate_payload(IntentSchema, raw)
    assert outcome.ok
    assert outcome.model.quantity == 2.0
    assert outcome.model.item == "salt"


def test_repair_does_not_invent_semantics():
    # Missing item cannot be repaired: we refuse rather than guess.
    assert not validate_payload(IntentSchema, '{"quantity": 2}').ok
    # Negative quantity is invalid, not silently clamped.
    assert not validate_payload(IntentSchema, '{"item": "salt", "quantity": -3}').ok


# --------------------------------------------------------------------------- #
# Degradation inside the flow
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("mode", ["prose", "empty", "wrong-hidden", "json-array", "not-json"])
def test_bad_model_never_corrupts_inventory_or_ledger(mode):
    w = _world()
    inventory_before = deepcopy(
        {nid: [i.model_dump() for i in n.inventory] for nid, n in w.neighbours.items()}
    )
    ledger_before = deepcopy(w.ledger)
    fairness_before = {nid: n.fairness_score for nid, n in w.neighbours.items()}

    result = Agent(w, FailingModel(mode)).handle("anyone have salt?")

    assert {nid: [i.model_dump() for i in n.inventory] for nid, n in w.neighbours.items()} == inventory_before
    assert w.ledger == ledger_before
    assert {nid: n.fairness_score for nid, n in w.neighbours.items()} == fairness_before

    # It degrades to *something* — never an exception, never a crash.
    assert result.request is not None
    assert w.stats["schema_failures"] >= 1
    assert any(l.action.value in ("schema_rejected", "model_call_failed") for l in w.logs)
    # And the user still gets a closure or an offer, not silence.
    assert result.closure or result.offers


def test_bad_reply_read_does_not_hallucinate_a_quantity():
    w = _world()
    result = Agent(w, FailingModel("prose")).handle("anyone have salt?")
    # With an unusable reply reading, no offer may be constructed from it.
    assert all(o.quantity > 0 for o in result.offers)
    assert w.stats["schema_failures"] >= 1


def test_ledger_only_ever_written_by_a_real_completion():
    """A bad model could have 'read' an offer, but the ledger needs a handover."""
    w = _world()
    agent = Agent(w, FailingModel("prose"))
    result = agent.handle("anyone have salt?")
    assert w.ledger == []
    if result.offers:
        agent.choose(result.request.id, result.offers[0].id)
        assert w.ledger == [], "choosing alone must not write the ledger"
        handover_id = list(w.handovers)[0]
        agent.finish_handover(handover_id)
        assert len(w.ledger) == 1


def test_stats_survive_a_bad_model():
    w = _world()
    Agent(w, FailingModel("not-json")).handle("anyone have salt?")
    assert isinstance(w.stats["requests"], int)
    assert w.stats["requests"] == 1
    assert w.stats["schema_failures"] >= 1


def test_decision_log_rejects_an_empty_reason():
    import pydantic

    from nearmind.models import DecisionLog, LogAction

    with pytest.raises(pydantic.ValidationError):
        DecisionLog(
            id="x",
            at=T0,
            clock_time="19:00",
            action=LogAction.NO_MATCH,
            reason="   ",
        )


def test_every_log_emitted_by_the_api_has_a_reason(client):
    """The mandatory-reason rule holds on the wire as well as in the model."""
    client.post("/api/chat", json={"message": "anyone have salt?"})
    logs = client.get("/api/logs").get_json()["data"]
    assert logs
    assert all(isinstance(l["reason"], str) and l["reason"].strip() for l in logs)
