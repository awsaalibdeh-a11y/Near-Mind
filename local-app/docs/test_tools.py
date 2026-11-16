"""Every MCP tool is called through FastMCP, so the declared return type is
validated exactly as it is for a real client. Nothing here touches a live
bridge or a real store: the database is a throwaway SQLite file and the Go
bridge is replaced by a fake (or by a port nothing listens on)."""
import asyncio
import sqlite3

import pytest
import requests

import main
import whatsapp

ME = "111@s.whatsapp.net"
BOB = "222@s.whatsapp.net"
GROUP = "333@g.us"


def call(tool, **args):
    """Invoke a tool the way an MCP client does; returns (content, structured)."""
    res = asyncio.run(main.mcp.call_tool(tool, args))
    content, data = res if isinstance(res, tuple) else (res, None)
    if isinstance(data, dict) and list(data) == ["result"]:   # FastMCP wraps non-object returns as {"result": ...}
        data = data["result"]
    return content, data


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "messages.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE chats (jid TEXT PRIMARY KEY, name TEXT, last_message_time TIMESTAMP);
        CREATE TABLE messages (id TEXT, chat_jid TEXT, sender TEXT, content TEXT,
            timestamp TIMESTAMP, is_from_me BOOLEAN, media_type TEXT, filename TEXT,
            url TEXT, media_key BLOB, file_sha256 BLOB, file_enc_sha256 BLOB, file_length INTEGER,
            PRIMARY KEY (id, chat_jid));
    """)
    conn.executemany("INSERT INTO chats VALUES (?,?,?)", [
        (BOB, "Bob", "2026-11-15T13:16:50"),
        (GROUP, "Family", "2026-11-15T12:00:00"),
    ])
    conn.executemany(
        "INSERT INTO messages (id, chat_jid, sender, content, timestamp, is_from_me, media_type) VALUES (?,?,?,?,?,?,?)",
        [
            ("m1", BOB, "222", "hello", "2026-11-15T13:10:00", 0, None),
            ("m2", BOB, "111", "hi bob", "2026-11-15T13:12:00", 1, None),
            ("m3", BOB, "222", "pic", "2026-11-15T13:16:50", 0, "image"),
            ("g1", GROUP, "333", "dinner?", "2026-11-15T12:00:00", 0, None),
        ])
    conn.commit()
    conn.close()
    monkeypatch.setattr(whatsapp, "MESSAGES_DB_PATH", str(path))
    return path


# ---- read tools: each must validate against its declared return type -------

def test_list_chats(db):
    _, data = call("list_chats", limit=5)
    chats = data
    assert {c["jid"] for c in chats} == {BOB, GROUP}
    bob = next(c for c in chats if c["jid"] == BOB)
    assert bob["name"] == "Bob" and bob["last_message"] == "pic"
    assert bob["is_group"] is False
    assert next(c for c in chats if c["jid"] == GROUP)["is_group"] is True


def test_list_messages_without_context(db):
    _, data = call("list_messages", limit=3, include_context=False)
    msgs = data
    assert [m["id"] for m in msgs] == ["m3", "m2", "m1"]
    assert msgs[0]["content"] == "pic" and msgs[0]["media_type"] == "image"
    assert msgs[1]["is_from_me"] is True and msgs[0]["chat_jid"] == BOB


def test_list_messages_with_context(db):
    _, data = call("list_messages", query="hi bob", include_context=True)
    assert [m["id"] for m in data] == ["m1", "m2", "m3"]


def test_list_messages_returns_records_not_text(db):
    out = whatsapp.list_messages(include_context=False)
    assert isinstance(out, list) and all(isinstance(m, whatsapp.Message) for m in out)


def test_search_contacts(db):
    _, data = call("search_contacts", query="bob")
    assert data == [{"phone_number": "222", "name": "Bob", "jid": BOB}]


def test_get_chat(db):
    _, data = call("get_chat", chat_jid=BOB)
    assert data["jid"] == BOB and data["last_message"] == "pic"


def test_get_chat_not_found_is_a_clear_error(db):
    with pytest.raises(Exception, match="not found"):
        call("get_chat", chat_jid="nope@s.whatsapp.net")


def test_get_direct_chat_by_contact(db):
    _, data = call("get_direct_chat_by_contact", sender_phone_number="222")
    assert data["jid"] == BOB


def test_get_contact_chats(db):
    _, data = call("get_contact_chats", jid=BOB)
    # NB: upstream returns one row per message here (DISTINCT over message columns); asserting the set is out of scope
    assert {c["jid"] for c in data} == {BOB}


def test_get_last_interaction(db):
    content, data = call("get_last_interaction", jid=BOB)
    text = data if isinstance(data, str) else content[0].text
    assert "pic" in text and "Bob" in text


def test_get_message_context(db):
    _, data = call("get_message_context", message_id="m2", before=1, after=1)
    assert data["message"]["id"] == "m2"
    assert [m["id"] for m in data["before"]] == ["m1"]
    assert [m["id"] for m in data["after"]] == ["m3"]


# ---- write tools: fake bridge, never a real send ---------------------------

class FakeResp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body, self.text = status, body or {}, str(body)

    def json(self):
        return self._body


@pytest.fixture
def fake_bridge(monkeypatch, tmp_path):
    calls = []

    def post(url, json=None, **kw):
        calls.append((url, json))
        if url.endswith("/send"):
            return FakeResp(200, {"success": True, "message": "Message sent to " + json["recipient"]})
        if url.endswith("/download"):
            return FakeResp(200, {"success": True, "message": "ok", "filename": "a.jpg", "path": "/tmp/a.jpg"})
        return FakeResp(404)

    monkeypatch.setattr(whatsapp.requests, "post", post)
    return calls


def test_send_message(fake_bridge):
    _, data = call("send_message", recipient="222", message="hi")
    assert data == {"success": True, "message": "Message sent to 222"}
    assert fake_bridge == [(whatsapp.WHATSAPP_API_BASE_URL + "/send", {"recipient": "222", "message": "hi"})]


def test_send_file(fake_bridge, tmp_path):
    f = tmp_path / "x.png"
    f.write_bytes(b"x")
    _, data = call("send_file", recipient="222", media_path=str(f))
    assert data["success"] is True
    assert fake_bridge[0][1] == {"recipient": "222", "media_path": str(f)}


def test_send_audio_message(fake_bridge, tmp_path):
    f = tmp_path / "x.ogg"
    f.write_bytes(b"x")
    _, data = call("send_audio_message", recipient="222", media_path=str(f))
    assert data["success"] is True


def test_download_media(fake_bridge):
    _, data = call("download_media", message_id="m3", chat_jid=BOB)
    assert data == {"success": True, "message": "Media downloaded successfully", "file_path": "/tmp/a.jpg"}


# ---- bridge / store unreachable --------------------------------------------

def test_bridge_down_send_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(whatsapp, "WHATSAPP_API_BASE_URL", "http://127.0.0.1:1/api")  # nothing listens here
    _, data = call("send_message", recipient="222", message="hi")
    assert data["success"] is False and "Request error" in data["message"]


def test_bridge_down_download_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(whatsapp, "WHATSAPP_API_BASE_URL", "http://127.0.0.1:1/api")
    _, data = call("download_media", message_id="m3", chat_jid=BOB)
    assert data["success"] is False


def test_store_missing_read_is_a_clear_error(tmp_path, monkeypatch):
    missing = tmp_path / "store" / "messages.db"
    monkeypatch.setattr(whatsapp, "MESSAGES_DB_PATH", str(missing))
    with pytest.raises(Exception, match="WhatsApp message store not found"):
        call("list_chats")
    assert not missing.exists()          # reading must never create an empty store
