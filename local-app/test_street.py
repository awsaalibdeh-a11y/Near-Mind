"""NearMind Street engine with a stubbed robot and stubbed neighbors. No OpenAI, no WhatsApp.
Run:  python -m pytest -q test_street.py
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture()
def app_mod(tmp_path):
    import importlib
    import app as mod
    importlib.reload(mod)
    mod.STATE_FILE = tmp_path / "state.json"
    return mod


def run(c, who, text, clock="13:00"):
    r = c.post("/api/street/run", json={"from": who, "text": text, "clock": clock})
    return [json.loads(l) for l in r.get_data(as_text=True).splitlines() if l.strip()]


def test_page_and_people(app_mod):
    c = app_mod.app.test_client()
    assert c.get("/street").status_code == 200
    d = c.get("/api/street/people").get_json()
    assert d["order"] == ["sedra", "osama", "sulaiman", "asma", "alwalid", "anas"]
    assert all("sleep" in p and "home" not in p for p in d["people"].values())     # inventories stay hidden


def test_full_flow_events_in_order(app_mod, monkeypatch):
    st = app_mod.STREET
    rounds = iter([
        {"think": "Asking two awake neighbors.", "parse": {"item": "movie buddy", "kind": "company", "urgency": "low"},
         "phase": "outreach", "status": {"osama": "asked", "anas": "asked"},
         "messages": [{"to": "osama", "text": "Movie with Sedra tonight?"}, {"to": "anas", "text": "Up for a movie?"}]},
        {"think": "Reporting back.", "phase": "relay", "status": {"osama": "offer", "anas": "no"},
         "messages": [{"to": "sedra", "text": "Osama is in! Want him?"}], "quick": ["Yes, Osama", "No thanks"]},
    ])
    monkeypatch.setattr(st, "robot_fn", lambda S, force: next(rounds))
    monkeypatch.setattr(st, "neighbor_fn", lambda S, n: {"osama": "Happy to, my friend", "anas": "nah sorry"}[n])
    ev = run(app_mod.app.test_client(), "sedra", "I need someone to watch a movie with me")
    kinds = [e["t"] for e in ev]
    assert ev[0] == {"t": "say", "from": "sedra", "to": "robot", "text": "I need someone to watch a movie with me"}
    assert kinds[-1] == "done" and "error" not in kinds
    says = [(e["from"], e["to"]) for e in ev if e["t"] == "say"]
    assert says == [("sedra", "robot"), ("robot", "osama"), ("robot", "anas"), ("osama", "robot"), ("anas", "robot"), ("robot", "sedra")]
    assert {"t": "quick", "options": ["Yes, Osama", "No thanks"]} in ev
    assert {"t": "status", "who": "anas", "state": "no"} in ev


def test_robot_cannot_mark_the_asker_or_unknown_people(app_mod, monkeypatch):
    st = app_mod.STREET
    monkeypatch.setattr(st, "robot_fn", lambda S, f: {"status": {"sedra": "asked", "ghost": "asked", "osama": "weird"},
                                                     "messages": [{"to": "ghost", "text": "hi"}, {"to": "sedra", "text": "On it!"}]})
    ev = run(app_mod.app.test_client(), "sedra", "need sugar")
    assert not [e for e in ev if e["t"] == "status"]
    assert [e["to"] for e in ev if e["t"] == "say" and e["from"] == "robot"] == ["sedra"]


def test_new_asker_starts_fresh(app_mod, monkeypatch):
    st = app_mod.STREET
    monkeypatch.setattr(st, "robot_fn", lambda S, f: {"messages": [{"to": S["asker"], "text": "ok"}]})
    c = app_mod.app.test_client()
    run(c, "sedra", "need sugar")
    run(c, "osama", "need a drill")
    S = st.sess("me")
    assert S["asker"] == "osama" and S["threads"]["sedra"] == []


def test_bad_requests_rejected(app_mod):
    c = app_mod.app.test_client()
    assert c.post("/api/street/run", json={"from": "nobody", "text": "hi"}).status_code == 400
    assert c.post("/api/street/run", json={"from": "sedra", "text": "  "}).status_code == 400


def test_model_failure_becomes_error_event(app_mod, monkeypatch):
    st = app_mod.STREET

    def boom(S, f):
        raise RuntimeError("timeout")
    monkeypatch.setattr(st, "robot_fn", boom)
    ev = run(app_mod.app.test_client(), "asma", "need a flashlight")
    assert any(e["t"] == "error" for e in ev) and ev[-1]["t"] == "done"
