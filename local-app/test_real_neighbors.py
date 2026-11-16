"""Real neighbors on WhatsApp, end to end through the server, with a FAKE bridge and a stubbed model.
Nothing is sent to WhatsApp or OpenAI.   Run:  python -m pytest -q test_real_neighbors.py
"""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture()
def A(monkeypatch, tmp_path):
    import importlib
    import app as mod
    importlib.reload(mod)
    monkeypatch.setattr(mod, "NB_FILE", tmp_path / "neighbors.json")
    mod.STATE_FILE = tmp_path / "state.json"            # plain assignment: late background threads must never write the real file
    mod.REAL.clear()
    mod.load_real()
    mod.SESS.clear()
    calls = []

    def fake_bridge(path, data=None, timeout=3):
        calls.append((path, data))
        if path == "/status":
            return {"state": "open"}
        return {"ok": True, "numbers": []}

    monkeypatch.setattr(mod, "bridge", fake_bridge)
    mod.calls = calls
    mod.neighbor_reply = lambda *a, **k: pytest.fail("a real neighbor must never be AI-simulated")
    mod._real_is_quiet = mod.is_quiet
    mod.is_quiet = lambda S: False                         # tests run at any hour; quiet-hours tests opt back in
    mod.REPLY_TIMEOUT = 3600
    return mod


def wait(cond, t=5):
    end = time.time() + t
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


def sends_to(A, number):
    return [d["text"] for p, d in A.calls if p == "/send" and d and d.get("to") == number]


def test_set_neighbor_renames_slot_and_allowlists(A):
    c = A.app.test_client()
    r = c.post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "+966 55 111 2222"}).get_json()
    assert r["neighbors"]["2"] == {"name": "Ali", "number": "966551112222"}
    assert A.PEOPLE[2]["name"] == "Ali" and A.KNOW[2]["name"] == "Ali"
    assert ("/allow", {"add": "966551112222"}) in A.calls
    assert c.get("/api/config").get_json()["neighbors"] == {"2": "Ali"}
    assert json.loads(A.NB_FILE.read_text())["2"]["number"] == "966551112222"


def test_bad_input_rejected(A):
    c = A.app.test_client()
    assert c.post("/api/wa/neighbors", json={"slot": 1, "name": "X", "number": "966551112222"}).status_code == 400
    assert c.post("/api/wa/neighbors", json={"slot": 2, "name": "", "number": "966551112222"}).status_code == 400
    assert c.post("/api/wa/neighbors", json={"slot": 2, "name": "X", "number": "123"}).status_code == 400
    c.post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "966551112222"})
    assert c.post("/api/wa/neighbors", json={"slot": 3, "name": "Dup", "number": "966551112222"}).status_code == 400


def test_first_message_is_opt_in_not_a_request(A, monkeypatch):
    A.app.test_client().post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "966551112222"})
    monkeypatch.setattr(A, "nearmind", lambda S, force: pytest.fail("opt-in must not run the agent"))
    A.app.test_client().post("/api/wa/incoming", json={"text": "hi", "from": "966551112222"})
    assert wait(lambda: sends_to(A, "966551112222"))
    sent = sends_to(A, "966551112222")
    assert len(sent) == 1 and "connected to NearMind" in sent[0]  # exactly one welcome, no agent run


def test_welcome_can_be_turned_off(A, monkeypatch):
    monkeypatch.setattr(A, "WELCOME_ON", False)
    A.app.test_client().post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "966551112222"})
    A.app.test_client().post("/api/wa/incoming", json={"text": "hi", "from": "966551112222"})
    assert wait(lambda: 2 in A.sess("me").get("joined", set()))
    time.sleep(0.3)
    assert sends_to(A, "966551112222") == []


def test_ask_goes_to_real_whatsapp_and_reply_drives_agent(A, monkeypatch):
    c = A.app.test_client()
    c.post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "966551112222"})
    S = A.sess("me")
    S["threads"][2] = [("me", "hi"), ("ai", "welcome")]
    S["joined"] = {2}                                            # already opted in
    seen = []

    def model(S_, force):
        seen.append(A.render(S_["threads"]))
        if len(seen) == 1:
            return {"phase": "outreach", "messages": [{"to": 2, "text": "Hi Ali, do you have a ladder Maya could borrow?"}]}
        return {"phase": "relay", "messages": [{"to": 1, "text": "Ali has a ladder for you!"}]}

    monkeypatch.setattr(A, "nearmind", model)
    ev = [json.loads(l) for l in c.post("/api/turn", json={"text": "need a ladder"}).get_data(as_text=True).splitlines() if l]
    assert sends_to(A, "966551112222") == ["Hi Ali, do you have a ladder Maya could borrow?"]   # plain text, no labels
    assert any("Waiting for a real reply" in e.get("text", "") for e in ev if e["t"] == "step")
    assert len(seen) == 1                                        # stopped to wait; did not re-ask

    c.post("/api/wa/incoming", json={"text": "yes got one", "from": "966551112222"})
    assert wait(lambda: len(seen) == 2)
    assert "Ali: yes got one" in seen[1]
    assert wait(lambda: any(m == ("ai", "Ali has a ladder for you!") for m in S["threads"][1]))

    # the answer was used; a later chat message from Ali is personal and NearMind stays out of it
    c.post("/api/wa/incoming", json={"text": "btw are you coming saturday?", "from": "966551112222"})
    time.sleep(0.5)
    assert len(seen) == 2


def test_unknown_number_gets_no_reply(A, monkeypatch):
    monkeypatch.setattr(A, "nearmind", lambda S, force: pytest.fail("must not answer someone's private chat"))
    A.app.test_client().post("/api/wa/incoming", json={"text": "hello", "from": "15550001111"})
    time.sleep(0.3)
    assert "wa:15550001111" not in A.SESS and not [c for c in A.calls if c[0] == "/send"]


def test_friends_mode_can_be_switched_on(A, monkeypatch):
    monkeypatch.setattr(A, "FRIENDS", True)
    monkeypatch.setattr(A, "nearmind", lambda S, force: {"messages": [{"to": 1, "text": "hey"}]})
    A.app.test_client().post("/api/wa/incoming", json={"text": "hello", "from": "15550001111"})
    assert wait(lambda: "wa:15550001111" in A.SESS)


def test_remove_restores_ai_neighbor(A):
    c = A.app.test_client()
    c.post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "966551112222"})
    c.post("/api/wa/neighbors", json={"slot": 2, "remove": True})
    assert A.PEOPLE[2]["name"] == "Ben" and 2 not in A.REAL
    assert ("/allow", {"remove": "966551112222"}) in A.calls


def test_undelivered_neighbor_message_warns_owner_on_whatsapp(A, monkeypatch):
    c = A.app.test_client()
    c.post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "966551112222"})
    real_fake = A.bridge

    def refusing(path, data=None, timeout=3):
        if path == "/send" and data and data.get("to") == "966551112222":
            raise OSError("HTTP Error 403: Forbidden")          # neighbor hasn't messaged first
        return real_fake(path, data, timeout)

    monkeypatch.setattr(A, "bridge", refusing)
    monkeypatch.setattr(A, "nearmind", lambda S, force: {"messages": [{"to": 2, "text": "Hi Ali, got a ladder?"}]})
    c.post("/api/turn", json={"text": "need a ladder"}).get_data()
    to_owner = [d["text"] for p, d in A.calls if p == "/send" and d and d.get("to") is None]
    assert any("Not delivered to Ali" in t for t in to_owner)


def test_self_chat_is_private_by_default(A, monkeypatch):
    c = A.app.test_client()
    replies = iter([{"messages": [{"to": 2, "text": "Ben, got salt?"}]}, {"messages": [{"to": 1, "text": "Ben has salt!"}]}])
    monkeypatch.setattr(A, "nearmind", lambda S, force: next(replies))
    monkeypatch.setattr(A, "neighbor_reply", lambda *a, **k: "yep")          # slot 2 is the AI neighbor here
    c.post("/api/turn", json={"text": "need salt"}).get_data()
    owner = [d["text"] for p, d in A.calls if p == "/send" and d and d.get("to") is None]
    assert any("Ben has salt!" in t for t in owner)
    assert not any("private chat with" in t for t in owner)                 # nothing NearMind said to/heard from neighbors


def test_owner_can_opt_in_to_see_neighbor_chats(A, monkeypatch):
    c = A.app.test_client()
    c.post("/api/wa/mirror", json={"neighbors": True})
    replies = iter([{"messages": [{"to": 2, "text": "Ben, got salt?"}]}, {"messages": [{"to": 1, "text": "Ben has salt!"}]}])
    monkeypatch.setattr(A, "nearmind", lambda S, force: next(replies))
    monkeypatch.setattr(A, "neighbor_reply", lambda *a, **k: "yep")
    c.post("/api/turn", json={"text": "need salt"}).get_data()
    owner = [d["text"] for p, d in A.calls if p == "/send" and d and d.get("to") is None]
    assert any("private chat with Ben" in t for t in owner)
    A.WA["neighbors"] = False


# ---------- slash commands + persistence ----------

def owner_msgs(A):
    return [d["text"] for p, d in A.calls if p == "/send" and d and d.get("to") is None]


def say(A, text):
    A.app.test_client().post("/api/wa/incoming", json={"text": text})       # self-chat: no "from"


def test_help_and_unknown_command_need_no_model(A, monkeypatch):
    monkeypatch.setattr(A, "nearmind", lambda S, force: pytest.fail("commands must not call the model"))
    say(A, "/help")
    say(A, "/whatever")
    assert "NearMind commands" in owner_msgs(A)[0]
    assert "don't know that command" in owner_msgs(A)[1]


def test_status_shows_real_neighbor_join_state(A, monkeypatch):
    A.app.test_client().post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "966551112222"})
    say(A, "/status")
    assert "Ali: real neighbor, hasn't messaged you yet" in owner_msgs(A)[-1]
    A.app.test_client().post("/api/wa/incoming", json={"text": "hi", "from": "966551112222"})
    assert wait(lambda: 2 in A.sess("me").get("joined", set()))
    say(A, "/status")
    assert "Ali: real neighbor, joined" in owner_msgs(A)[-1]
    assert "Mrs. Cohen: AI neighbor" in owner_msgs(A)[-1]


def test_personal_messages_from_a_joined_neighbor_are_ignored(A, monkeypatch):
    A.app.test_client().post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "966551112222"})
    A.app.test_client().post("/api/wa/incoming", json={"text": "hi", "from": "966551112222"})
    assert wait(lambda: 2 in A.sess("me").get("joined", set()))
    monkeypatch.setattr(A, "nearmind", lambda S, force: pytest.fail("NearMind asked Ali nothing; it must stay silent"))
    A.app.test_client().post("/api/wa/incoming", json={"text": "Make up your mind then let me know", "from": "966551112222"})
    time.sleep(0.4)
    assert len(sends_to(A, "966551112222")) == 1                 # only the one welcome from joining, nothing more


def test_new_request_stops_waiting_on_old_questions(A):
    S = A.sess("me")
    S["waiting"] = {2}
    say(A, "/new")
    assert S["waiting"] == set()


def test_reset_needs_confirmation(A):
    S = A.sess("me")
    S["ledger"].append({"id": 1, "item": "ladder", "frm": 2, "kind": "lend", "open": True, "since": "10:00", "turn": 1})
    say(A, "/reset")
    assert S["ledger"]                                          # nothing forgotten yet
    say(A, "no")                                                # anything else cancels; "no" goes to the agent normally
    say(A, "yes")
    assert S["ledger"], "a stray 'yes' after cancelling must not wipe memory"
    say(A, "/reset")
    say(A, "yes")
    assert S["ledger"] == []


def test_state_survives_restart(A, monkeypatch):
    S = A.sess("me")
    S["mem"][2].append("has a ladder in the garage")
    S["history"].append({"item": "salt", "who": "Ben", "req": "Maya", "at": "19:00"})
    S["joined"] = {2}
    A.save_state()
    A.SESS.clear()
    A.load_state()
    S2 = A.sess("me")
    assert S2["mem"][2] == ["has a ladder in the garage"]
    assert S2["history"][0]["item"] == "salt" and S2["joined"] == {2}


# ---------- quiet hours + reply timeout ----------

def setup_joined_ali(A):
    A.app.test_client().post("/api/wa/neighbors", json={"slot": 2, "name": "Ali", "number": "966551112222"})
    S = A.sess("me")
    S["joined"] = {2}
    return S


def test_quiet_hours_hold_then_send_on_command(A, monkeypatch):
    S = setup_joined_ali(A)
    A.is_quiet = A._real_is_quiet
    S["clock"] = "23:30"                                        # simulated street clock: late
    monkeypatch.setattr(A, "schedule_morning", lambda S: None)
    monkeypatch.setattr(A, "nearmind", lambda S, force: {"parse": {"item": "ladder", "urgency": "low"},
                                                        "messages": [{"to": 2, "text": "Hi Ali, got a ladder?"}]})
    A.app.test_client().post("/api/turn", json={"text": "need a ladder tomorrow"}).get_data()
    assert sends_to(A, "966551112222") == []                    # nothing at 23:30
    assert any("late to message Ali" in t for t in owner_msgs(A))
    say(A, "/status")
    assert "Held until 08:00" in owner_msgs(A)[-1]
    say(A, "/send")
    assert sends_to(A, "966551112222") == ["Hi Ali, got a ladder?"]
    assert 2 in S["waiting"] and S["held"] == []


def test_urgent_request_goes_out_at_night(A, monkeypatch):
    S = setup_joined_ali(A)
    A.is_quiet = A._real_is_quiet
    S["clock"] = "23:30"
    monkeypatch.setattr(A, "nearmind", lambda S, force: {"parse": {"item": "fire extinguisher", "urgency": "High - urgent"},
                                                        "messages": [{"to": 2, "text": "Ali, urgent: extinguisher?"}]})
    A.app.test_client().post("/api/turn", json={"text": "kitchen fire need extinguisher"}).get_data()
    assert sends_to(A, "966551112222") == ["Ali, urgent: extinguisher?"]


def test_no_reply_nudges_owner(A, monkeypatch):
    S = setup_joined_ali(A)
    A.REPLY_TIMEOUT = 0.2
    monkeypatch.setattr(A, "nearmind", lambda S, force: {"messages": [{"to": 2, "text": "Hi Ali, got a ladder?"}]})
    A.app.test_client().post("/api/turn", json={"text": "need a ladder"}).get_data()
    assert wait(lambda: any("hasn't replied" in t for t in owner_msgs(A)), 3)


def test_reply_in_time_means_no_nudge(A, monkeypatch):
    S = setup_joined_ali(A)
    A.REPLY_TIMEOUT = 0.5
    replies = iter([{"messages": [{"to": 2, "text": "Hi Ali, got a ladder?"}]}, {"messages": [{"to": 1, "text": "Ali has one"}]}])
    monkeypatch.setattr(A, "nearmind", lambda S, force: next(replies))
    A.app.test_client().post("/api/turn", json={"text": "need a ladder"}).get_data()
    A.app.test_client().post("/api/wa/incoming", json={"text": "yes", "from": "966551112222"})
    time.sleep(1.0)
    assert not any("hasn't replied" in t for t in owner_msgs(A))


def test_release_message_does_not_wait_or_nudge(A, monkeypatch):
    S = setup_joined_ali(A)
    A.REPLY_TIMEOUT = 0.2
    monkeypatch.setattr(A, "nearmind", lambda S_, force: {"status": {"2": "done"},
                                                         "messages": [{"to": 2, "text": "All sorted, thanks anyway Ali!"},
                                                                      {"to": 1, "text": "Done, Ali released."}]})
    A.app.test_client().post("/api/turn", json={"text": "ok go with the other one"}).get_data()
    assert sends_to(A, "966551112222") == ["All sorted, thanks anyway Ali!"]
    assert 2 not in S.get("waiting", set())
    time.sleep(0.6)
    assert not any("hasn't replied" in t for t in owner_msgs(A))


def test_closed_request_leaves_nothing_pending(A, monkeypatch):
    S = setup_joined_ali(A)
    S["waiting"] = {2}
    monkeypatch.setattr(A, "nearmind", lambda S_, force: {"phase": "closed", "messages": [{"to": 1, "text": "All done!"}]})
    A.app.test_client().post("/api/turn", json={"text": "thanks!"}).get_data()
    assert S["waiting"] == set()


def test_model_failure_is_reported_on_whatsapp(A, monkeypatch):
    def boom(S, force):
        raise RuntimeError("upstream timeout")
    monkeypatch.setattr(A, "nearmind", boom)
    say(A, "anyone have salt?")
    assert wait(lambda: any("couldn't finish that" in t for t in owner_msgs(A)))


def test_command_failure_is_reported(A, monkeypatch):
    monkeypatch.setattr(A, "status_text", lambda S: 1 / 0)
    say(A, "/status")
    assert any("command failed" in t for t in owner_msgs(A))
