"""The MCP adapter is exercised on the wire against a stub MCP server.

This does not contact WhatsApp. It proves the adapter speaks MCP JSON-RPC over
stdio correctly, calls the right tools with the right arguments, and parses
both send results and the upstream's formatted message text.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from bridge.transport import McpStdioTransport, TransportError

STUB = Path(__file__).parent / "fake_mcp_server.py"


@pytest.fixture()
def log_path(tmp_path):
    return tmp_path / "calls.ndjson"


@pytest.fixture()
def transport(log_path):
    t = McpStdioTransport(
        stdio_command=[sys.executable, str(STUB), str(log_path)],
        contacts={"karim": "111@s.whatsapp.net"},
        timeout_seconds=10,
    )
    yield t
    t.close()


def calls(log_path):
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text().splitlines()]


def test_send_message_calls_the_right_tool(transport, log_path):
    mid = transport.send_text("111@s.whatsapp.net", "Any ladder?")
    assert mid
    found = calls(log_path)
    assert len(found) == 1
    assert found[0]["tool"] == "send_message"
    assert found[0]["args"] == {"recipient": "111@s.whatsapp.net", "message": "Any ladder?"}


def test_fetch_inbound_parses_formatted_lines(transport):
    msgs = transport.fetch_inbound(since=None)
    assert len(msgs) == 1
    m = msgs[0]
    assert m.content == "yes I have one ladder"
    assert m.sender_key == "111@s.whatsapp.net"
    assert m.is_from_me is False
    assert m.timestamp.year == 2026


def test_fetch_inbound_dedupes_across_polls(transport):
    assert len(transport.fetch_inbound(since=None)) == 1
    assert transport.fetch_inbound(since=None) == []


def test_resolve_key(transport):
    assert transport.resolve_key("karim") == "111@s.whatsapp.net"
    assert transport.resolve_key("nobody") is None


def test_missing_server_binary_surfaces_as_oserror():
    with pytest.raises(OSError):
        McpStdioTransport(stdio_command=["/nonexistent/mcp-server"], contacts={})


def test_send_failure_raises_transport_error():
    """If WhatsApp reports success=False, the adapter must not pretend."""
    t = McpStdioTransport.__new__(McpStdioTransport)
    t._request = lambda method, params=None: {
        "content": [
            {"type": "text", "text": json.dumps({"success": False, "message": "no such number"})}
        ]
    }
    with pytest.raises(TransportError, match="no such number"):
        t.send_text("111@s.whatsapp.net", "hi")
