"""Server tests for NearMind. No network, no OpenAI, no WhatsApp: the model is stubbed.

Run:  python -m pytest -q test_app.py
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


@pytest.fixture()
def A(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("NM_PUBLIC", "0")
    import importlib
    import app as mod
    importlib.reload(mod)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)   # .env may have set it during reload
    mod.STATE_FILE = tmp_path / "state.json"            # plain assignment: late background threads must never write the real file
    mod.SESS.clear()
    return mod


def ndjson(resp):
    return [json.loads(line) for line in resp.get_data(as_text=True).splitlines() if line.strip()]


def test_starts_without_openai_key(A):
    c = A.app.test_client()
    assert c.get("/api/config").get_json()["llm"] is False
    h = c.get("/api/health").get_json()
    assert h["ok"] is True and h["llm"] is False


def test_live_turn_without_key_reports_clear_error(A):
    ev = ndjson(A.app.test_client().post("/api/turn", json={"text": "anyone have salt?"}))
    err = [e for e in ev if e["t"] == "error"]
    assert err and "OPENAI_API_KEY" in err[0]["error"]
    assert ev[-1]["t"] == "done"


def test_empty_message_rejected(A):
    r = A.app.test_client().post("/api/turn", json={"text": "   "})
    assert r.status_code == 400


def test_bad_since_does_not_500(A):
    r = A.app.test_client().get("/api/log?since=abc")
    assert r.status_code == 200 and "events" in r.get_json()


def test_malformed_model_message_is_skipped_not_fatal(A, monkeypatch):
    replies = iter([
        {"phase": "relay", "messages": [{"to": "Maya", "text": "bad address"}, {"to": 1, "text": "Hi Maya, on it!"}]},
    ])
    monkeypatch.setattr(A, "nearmind", lambda S, force: next(replies))
    ev = ndjson(A.app.test_client().post("/api/turn", json={"text": "hi"}))
    assert not [e for e in ev if e["t"] == "error"]
    texts = [e["text"] for e in ev if e["t"] == "msg" and e["who"] == "ai"]
    assert texts == ["Hi Maya, on it!"]
