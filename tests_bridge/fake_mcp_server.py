"""A tiny MCP-over-stdio server used to prove the adapter's wire behaviour.

Implements just enough of MCP for :class:`McpStdioTransport`: initialize,
notifications/initialized, and tools/call for ``send_message`` /
``list_messages``. Records every send to a file so the test can assert the
exact JSON-RPC that reached "WhatsApp".
"""

from __future__ import annotations

import json
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else ""


def reply(id_, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": id_, "result": result}) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    method = msg.get("method")
    mid = msg.get("id")

    if method == "initialize":
        reply(mid, {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {"name": "stub"}})
    elif method == "notifications/initialized":
        continue
    elif method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        if LOG:
            with open(LOG, "a") as fh:
                fh.write(json.dumps({"tool": name, "args": args}) + "\n")
        if name == "send_message":
            reply(mid, {"content": [{"type": "text", "text": json.dumps({"success": True, "message": "sent"})}]})
        elif name == "list_messages":
            text = "[2026-11-14 18:05:00] Chat: Karim From: Karim: yes I have one ladder"
            reply(mid, {"content": [{"type": "text", "text": text}]})
        else:
            reply(mid, {"content": [{"type": "text", "text": "unknown tool"}]})
    elif mid is not None:
        reply(mid, None)
