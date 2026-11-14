"""HTTP contract tests — the shape the UI builds against.

If these break, a frontend build breaks. They assert the envelope, the enums,
the error codes and the full happy path over the wire.
"""


def _data(resp):
    body = resp.get_json()
    assert body["ok"] is True
    assert body["error"] is None
    return body["data"]


def _error(resp, code):
    body = resp.get_json()
    assert body["ok"] is False
    assert body["data"] is None
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    return body["error"]


def test_envelope_on_every_success(client):
    for path in ("/api/health", "/api/state", "/api/neighbours", "/api/contract", "/api/dashboard"):
        body = client.get(path).get_json()
        assert set(body) == {"ok", "data", "error"}
        assert body["ok"] is True and body["error"] is None


def test_unknown_route_uses_error_envelope(client):
    _error(client.get("/api/nope"), "not_found")


def test_chat_full_flow(client, world_from_app):
    # Give a second neighbour salt so the release path is genuinely exercised.
    from nearmind.models import InventoryItem

    world_from_app.neighbours["ali"].inventory.append(
        InventoryItem(item="salt", quantity=0.5, unit="kg")
    )
    data = _data(client.post("/api/chat", json={"message": "anyone have salt?"}))
    assert data["request"]["intent"]["item"] == "salt"
    assert data["offers"]
    offer = data["offers"][0]
    assert offer["safety"]["status"] == "safe"
    assert data["recommendation"]["offer_id"] == offer["id"]
    assert data["skipped"]

    chosen = _data(
        client.post(
            f"/api/requests/{data['request']['id']}/choose",
            json={"offer_id": offer["id"]},
        )
    )
    handover = chosen["handover"]
    assert handover["state"] == "proposed"
    assert chosen["released"]

    completed = _data(client.post(f"/api/handovers/{handover['id']}/complete"))
    assert completed["ledger"]["direction"] == "maryam_owes"

    req = _data(client.get(f"/api/requests/{data['request']['id']}"))
    assert req["request"]["status"] == "fulfilled"
    assert req["threads"]


def test_chat_requires_a_message(client):
    _error(client.post("/api/chat", json={}), "message_required")
    _error(client.post("/api/chat", json={"message": "   "}), "message_required")


def test_availability_requires_reason(client):
    _error(
        client.post("/api/neighbours/karim/availability", json={"state": "busy"}),
        "reason_required",
    )


def test_busy_requires_a_window(client):
    _error(
        client.post(
            "/api/neighbours/karim/availability",
            json={"state": "busy", "reason": "on a call"},
        ),
        "busy_needs_window",
    )


def test_invalid_availability_state(client):
    _error(
        client.post(
            "/api/neighbours/karim/availability",
            json={"state": "sleeping", "reason": "nap"},
        ),
        "invalid_state",
    )


def test_availability_round_trip(client):
    data = _data(
        client.post(
            "/api/neighbours/karim/availability",
            json={"state": "not_at_home", "reason": "out at the gym", "set_by": "whatsapp"},
        )
    )
    assert data["state"] == "not_at_home"
    assert data["set_by"] == "whatsapp"
    neighbour = _data(client.get("/api/neighbours/karim"))
    assert neighbour["availability"]["state"] == "not_at_home"
    assert neighbour["availability"]["reason"] == "out at the gym"


def test_clock_advance_fires_expiry(client):
    data = _data(client.post("/api/clock", json={"advance_minutes": 25}))
    assert "expiry_outcomes" in data
    assert data["clock"] == "19:25"


def test_clock_rejects_garbage(client):
    _error(client.post("/api/clock", json={}), "missing_time")
    _error(client.post("/api/clock", json={"advance_minutes": "soon"}), "invalid_minutes")


def test_dashboard_and_digest(client):
    client.post("/api/chat", json={"message": "anyone have salt?"})
    dash = _data(client.get("/api/dashboard"))
    assert dash["stats"]["requests"] == 1
    assert "karim" in dash["balance"]
    digest = _data(client.get("/api/digest"))
    assert digest["lines"]


def test_ledger_and_export(client):
    data = _data(client.post("/api/chat", json={"message": "anyone have salt?"}))
    offer = data["offers"][0]
    client.post(f"/api/requests/{data['request']['id']}/choose", json={"offer_id": offer["id"]})
    hid = _data(client.get("/api/handovers"))[0]["id"]
    client.post(f"/api/handovers/{hid}/complete")

    ledger = _data(client.get("/api/ledger"))
    assert len(ledger["entries"]) == 1
    assert ledger["reciprocity"][0]["neighbour_id"] == "karim"

    export = _data(client.get("/api/export"))
    assert export["threads"]
    for thread in export["threads"]:
        assert thread["neighbour"]
        assert thread["messages"]


def test_reverse_request_endpoint(client):
    client.post("/api/chat", json={"message": "anyone have salt?"})
    data = _data(
        client.post(
            "/api/inbound/reverse-request",
            json={"neighbour_id": "karim", "item": "sugar"},
        )
    )
    # No debt yet (handover not completed), so no forced priority.
    assert data["route_to_maryam_first"] is False


def test_scenarios_listed_and_runnable(client):
    scenarios = _data(client.get("/api/scenarios"))
    ids = {s["id"] for s in scenarios}
    assert {"safety_veto", "urgency_low_2am", "urgency_high_2am", "availability_routing"} <= ids

    run = _data(client.post("/api/scenarios/safety_veto/run"))
    assert run["id"] == "safety_veto"
    assert run["flow"]["offers"] == []
    assert any(l["action"] == "safety_veto" for l in run["logs"])


def test_contract_documents_every_route(client):
    contract = _data(client.get("/api/contract"))
    documented = {e["path"] for e in contract["endpoints"]}
    # Every rule the UI relies on has a documented endpoint.
    for must in (
        "/api/chat",
        "/api/requests/<id>/choose",
        "/api/neighbours/<id>/availability",
        "/api/handovers/sweep",
        "/api/logs",
        "/api/ledger",
        "/api/scenarios/<id>/run",
    ):
        assert must in documented
    assert set(contract["enums"]) >= {"availability", "urgency", "handover_state"}
