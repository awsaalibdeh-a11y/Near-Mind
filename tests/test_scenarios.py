"""The showcase scenarios themselves.

These are what the Showcase surface replays, so they are tested as product
artefacts: determinism, the required demos, and the reasoning each one must
be able to show.
"""

import json

import pytest

from nearmind.scenarios import SCENARIOS


REQUIRED = ("safety_veto", "urgency_low_2am", "urgency_high_2am", "availability_routing")


@pytest.mark.parametrize("scenario_id", REQUIRED)
def test_required_scenarios_exist_and_run(scenario_id):
    scenario = SCENARIOS[scenario_id]
    result = scenario["fn"]()
    assert result["logs"], "a scenario that logs nothing shows no reasoning"
    assert all(l["reason"].strip() for l in result["logs"])


def test_safety_veto_scenario_shows_the_veto():
    data = SCENARIOS["safety_veto"]["fn"]()
    assert data["flow"]["offers"] == []
    vetoes = [l for l in data["logs"] if l["action"] == "safety_veto"]
    assert vetoes
    assert any("creaky" in l["reason"] for l in vetoes)
    assert any("scarcity" in l["reason"] or "only one available" in l["reason"] for l in vetoes)


def test_urgency_pair_contrasts_cleanly():
    low = SCENARIOS["urgency_low_2am"]["fn"]()
    high = SCENARIOS["urgency_high_2am"]["fn"]()

    low_contacts = {t["neighbour_id"] for t in low["threads"] if t["messages"]}
    assert low_contacts == set()
    assert any(l["action"] == "no_match" for l in low["logs"])

    assert any(l["action"] == "urgency_override" for l in high["logs"])
    assert high["stats"]["wakes"] >= 1
    assert high["flow"]["offers"]


def test_availability_routing_scenario_never_contacts_the_out_neighbour():
    data = SCENARIOS["availability_routing"]["fn"]()
    contacted = {t["neighbour_id"] for t in data["threads"] if t["messages"]}
    assert "karim" not in contacted
    assert any(
        l["action"] == "skipped_neighbour" and "not at home" in l["reason"] for l in data["logs"]
    )
    assert data["flow"]["offers"]


@pytest.mark.parametrize("scenario_id", list(SCENARIOS))
def test_scenarios_are_deterministic(scenario_id):
    """Replay must be identical — the Showcase pauses and replays them."""
    a = SCENARIOS[scenario_id]["fn"]()
    b = SCENARIOS[scenario_id]["fn"]()

    def strip(payload):
        return json.loads(
            json.dumps(payload, default=str).replace("ho_", "HO_").replace("req_", "REQ_")
        )

    # Compare on substance, not on random ids.
    assert [l["action"] for l in a["logs"]] == [l["action"] for l in b["logs"]]
    assert [l["clock_time"] for l in a["logs"]] == [l["clock_time"] for l in b["logs"]]
    assert a.get("stats") == b.get("stats")
    assert [n["availability"]["state"] for n in a.get("neighbours", [])] == [
        n["availability"]["state"] for n in b.get("neighbours", [])
    ]


def test_handover_expiry_scenario_reaches_a_pivot():
    data = SCENARIOS["handover_expiry_pivot"]["fn"]()
    actions = [o["action"] for o in data["expiry_outcomes"]]
    assert actions == ["checked_back", "pivoted"]
    assert any(l["action"] == "handover_pivoted" for l in data["logs"])


def test_reciprocity_scenario_settles_one_debt():
    data = SCENARIOS["reciprocity"]["fn"]()
    assert data["route_to_maryam_first"] is True
    assert any(l["action"] == "reciprocity_confirmed" for l in data["logs"])


def test_third_neighbour_name_is_configurable(monkeypatch):
    """Never hard-coded: the cast changes with config."""
    monkeypatch.setenv("NEARMIND_THIRD_NAME", "Layla")
    from nearmind.config import seed_neighbours

    names = [n["name"] for n in seed_neighbours("Layla")]
    assert "Layla" in names
