# bridge/ — NearMind WhatsApp bridge

The real-world proof: wraps the workspace `whatsapp` MCP server so NearMind's
neighbourhood logic can talk to **real people** on one linked WhatsApp account.

```python
from bridge import WhatsAppBridge, ContactRef

b = WhatsAppBridge(contacts={"karim": ContactRef("karim", "Karim")})
b.receive()                                    # validated inbound events
b.send("karim", "Any ladder?", urgent=False)   # honours STOP/BUSY + rate limits
b.report()                                     # dry_run | live, counters, guards
```

- Full interface, STOP/BUSY state machine, rate-limit numbers and the real-send
  gate: [`docs/BRIDGE.md`](../docs/BRIDGE.md)
- Tests: `./bridge/run_tests.sh` — 132 passing, no network, no account, no key
- **Dry-run by default.** No real number can receive a message unless
  `dry_run=False` **and** `allow_live_sends=True` are both set by an operator.
