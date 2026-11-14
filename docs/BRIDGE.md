# NearMind WhatsApp bridge

The bridge is the proof that NearMind's neighbourhood logic works on **real
people**, not only on the three AI neighbours. The sandbox is the test bench;
this is the wire.

It wraps the workspace `whatsapp` MCP server (`lharries/whatsapp-mcp`: a Go
`whatsapp-bridge` plus a 12-tool Python MCP server). It does **not** implement
a WhatsApp client, and it never learns the wire protocol beyond the two tools
it needs.

> **Honest identity model.** The bridge is **one linked WhatsApp account**. A
> neighbour listed here is a *simulated identity* unless a real contact was
> explicitly mapped to it. Until that mapping exists and an operator flips the
> live switch (§7), every "send" goes to an in-memory outbox. The UI badge
> (`sandbox: true`) is driven by `BridgeStatus` and is never inferred.

---

## 1. The interface the backend calls

Four verbs, in `bridge/core.py`:

```python
from bridge import WhatsAppBridge, ContactRef

bridge = WhatsAppBridge(contacts={
    "karim": ContactRef("karim", "Karim"),
    # ...one per neighbour
})

bridge.resolve_contact("karim")           # -> ResolvedContact | None
bridge.send("karim", "Any ladder?", urgent=False)   # -> OutboundReceipt
bridge.receive()                           # -> InboundBatch
bridge.report()                            # -> BridgeStatus
```

Everything else (`availability`, `limiter`, `transport`) is reachable for the
dashboard and inspector, but the flow should need only these four.

### `resolve_contact(contact_id) -> ResolvedContact | None`

```python
ResolvedContact(
    contact_id="karim",
    display_name="Karim",
    has_real_wire=True,          # False = simulated only, sends fail closed
    availability=Availability(state=..., source=..., since=..., reason=..., expires_at=...),
)
```

`None` means "no such neighbour". The caller must not guess — `send` refuses
unknown ids for the same reason.

### `send(contact_id, body, urgent=False) -> OutboundReceipt`

Total: returns a receipt and never raises for a rule violation.

```python
OutboundReceipt(
    outcome=SendOutcome.SENT | REFUSED | FAILED | SUPPRESSED,
    contact=ContactRef(...),
    sent_at=datetime,
    message_id="...",
    reason=None | "stopped" | "not_at_home" | "busy" | "burst" | "day_cap"
                | "silence_backoff" | "duplicate" | "unknown_contact"
                | "simulated_identity" | "transport_error",
    detail="Karim sent STOP — not messaged again until they resume",
    daily_count=3,
)
```

`outcome` is the only field to switch on; `reason` is a stable slug; `detail`
is display text safe to copy into a decision log. A **`SUPPRESSED`** outcome is
not an error — it is NearMind choosing not to. A **`REFUSED`** outcome means a
rate rule; schedule the retry from `limiter.decide(...).retry_after_seconds`.

Check order (this is the product, in order):

| # | Check | On failure |
|---|-------|-----------|
| 1 | contact exists | `REFUSED / unknown_contact` |
| 2 | **STOP** in force | `SUPPRESSED / stopped` — **no urgent override, ever** |
| 3 | not at home (incl. "out") | `SUPPRESSED / not_at_home` |
| 4 | busy, and `urgent=False` | `SUPPRESSED / busy` |
| 5 | simulated identity, no real number | `SUPPRESSED / simulated_identity` |
| 6 | rate limiter | `REFUSED / <refusal>` |
| 7 | transport | `FAILED / transport_error` or `SENT` |

One carve-out: the **acknowledgement** of `STOP` / `BUSY` (sent internally by
`receive`, never by the flow) is exempt from steps 2, 3 and 6 so the person
always learns the command landed. It is the *only* message a stopped person can
receive.

### `receive() -> InboundBatch`

```python
InboundBatch(
    events=(InboundEvent(...), ...),        # validated, typed
    failures=(ValidationFailure(...), ...), # rejected, with a stable reason
    transitions=(("karim", Transition(before, after, changed=True)), ...),
)
```

Validation is **total** — it never raises. Each raw message is resolved to a
`ContactRef`, checked (sender, id, timestamp, size, group/self exclusion) and
classified as `command | text | media | reaction | unknown`. The event is
**already applied** to availability by the time it is returned: a crash in the
caller cannot lose a `STOP`.

The backend should:
- render `events` of kind `text` / `media` / `unknown` through the normal
  clarification flow (they are neighbour replies);
- ignore `reaction`;
- treat `events` of kind `command` as *already handled* (availability is
  updated, acknowledgement is sent) — use them only to log a decision and let
  the UI redraw the window;
- log `failures` as decisions with `action="inbound_rejected"` and the
  `failure.reason` slug. A malformed reply must never touch the ledger,
  inventory or stats.

### `report() -> BridgeStatus`

`mode` (`dry_run` / `live`), `transport` (`fake` / `mcp_stdio`), `sandbox`,
`linked_identity`, `counters` (`sent`, `suppressed`, `refused`, `failed`,
`inbound`, `invalid_inbound`), per-contact `guards` (daily usage, burst tokens,
unanswered count, availability snapshot) and `last_poll_at`. This is the
single source for the "sandbox vs real bridge" badge and the bridge health tile.

### `may_contact(contact_id, asleep=False) -> (bool, reason)`

The cheapest combined pre-flight (availability **and** guardrail volume) for
the eligibility filter. If it says no, put `reason` in the decision log — it is
already written as the inspector's sentence.

---

## 2. The STOP / BUSY state machine

One wire state per neighbour (the UI contract asks for exactly
`available | busy | not_at_home`); STOP is **sticky unavailability**.

```
  AVAILABLE ──── BUSY ──────────────── expire(window) ──► AVAILABLE
              ("busy", "busy 30m")       (auto, own window)

  *ANY* ──────── STOP ──────────────── sticky, expires_at = None
              ("stop", "dont msg me")    └─► only RESUME lifts it

  *ANY* ──────── STOP <t> ───────────── BUSY t, source = whatsapp_stop
              ("stop 2h")                └─► anti-spam applies while it lasts,
                                              then auto-expires to AVAILABLE

  STOPPED + BUSY ────────────────────── ignored; STOP wins, ack says so
```

Rules, all enforced in `availability.py`:

| Event | From any state | Result |
|-------|----------------|--------|
| `STOP` | available / busy / out | `not_at_home`, source `whatsapp_stop`, `expires_at=None`. Sticky until `RESUME`. |
| `STOP` again | already stopped | no change; **`since` is preserved** (so the inspector doesn't lie about when it began). Still acknowledged. |
| `BUSY` / `BUSY 30m` | available / busy | `busy` with `expires_at = now + window` (default 1 h, max 12 h). Re-sending `BUSY` **replaces** the window. |
| `BUSY` while **stopped** | — | **no change** — STOP takes precedence. The acknowledgement says so ("You're still set to STOP…"). A BUSY must never weaken a STOP, or a stray word could reopen a channel the person closed. |
| `STOP 2h` | any | `busy` with `expires_at = now+2h`, **source `whatsapp_stop`** → anti-spam applies while it lasts, then auto-expires to available. |
| `RESUME` | any | `available`. The only way out of a sticky STOP. |
| `HELP` | any | no state change. Answered. |
| sandbox write | any | sets scripted state **unless** the contact has a real STOP — a scenario may never override a real person's STOP. |

**Idempotence** is a hard property and is tested: `apply_command` is total for
every (state, command) pair; a no-op returns `changed=False` with a note. A
second bare `STOP` keeps the original `since`.

**Expiry** is lazy on read *and* swept on every `receive()` tick, so the
inspector's `since` is live without a background job.

**Combination with the clock** (as in the product spec): `asleep` is passed to
`may_contact` as a separate boolean — *home but asleep* is expressible without
merging it into the state, which is exactly what the UI required.

Command tolerance: case, accents, whitespace, punctuation, repetition
(`stop stop`), durations (`busy 30m`, `busy for 2 hours`, `brb 10 min`,
`stop 2h`) and common phrasings (`don't message me`, `im back`, `not now`) are
accepted. Anything ambiguous is **not** treated as a command (`stop by
anytime`, `busy street out here`), because a false STOP from prose is worse
than a missed one — the person can always send `STOP` alone. Parsing never
raises.

---

## 3. Validated inbound — the rule that protects state

`validate_inbound(payload, contact_index=..., now=..., max_age_seconds=...)`
returns `InboundEvent | ValidationFailure`. It never raises; a garbage
transport item becomes a failure, not an exception.

Rejected (each with a stable `reason`): non-mapping payload, missing sender,
sender not a known neighbour, message id missing, unparseable timestamp,
`is_from_me`, group chats, body > 1 MB (`too_large`), and anything older than
the replay window (`unsupported_type`) — a restart must not replay a backlog
`STOP`.

Normalised before it can reach agent state: invisible / control characters
stripped, whitespace trimmed, body capped at 4 000 chars (marked with `…` when
truncated). An unknown number can never issue `STOP` for a neighbour, and a
group chat is never mined for commands.

Tests in `tests_bridge/test_inbound_schema.py` (every malformed shape) and
`tests_bridge/test_bridge_e2e.py::test_malformed_inbound_is_separated_from_events`.

---

## 4. Rate limits — the numbers and why

Configured in `RateLimitConfig`; defaults below. Each stops a specific failure
the others miss.

| Rule | Default | Why this number |
|------|---------|-----------------|
| **Burst** | 4 tokens, refill 1 / 60 s | A favour thread never needs more than a few messages inside a minute. Four is enough for "ask → clarify → confirm → nudge", and one per 60 s is already faster than a human reads and replies. Stops a runaway loop. |
| **Daily cap** | 5 / rolling 24 h | One full favour thread is ~5 messages (ask, clarify, confirm handover, release, plus slack). One message every ten minutes for eight hours is exactly the slow spam the bucket cannot see — the day cap is. |
| **Silence backoff** | after 2 unanswered, wait `10 min × 2ⁿ` since the last send, capped at 6 h | The "thread went quiet" rule. Two is the point where a non-reply stops looking like "still typing". Doubling, capped, so it degrades into silence instead of a campaign. |
| **Hard refusal** | 4 unanswered | After four unanswered messages a person is not going to answer. Refuse entirely (`retry_after=None`); a human can reset with any reply. |
| **Duplicate** | identical body to the same contact within 15 min | A retry that repeats the same text reads as a broken bot. Whitespace-insensitive. |
| **Replay window** | 6 h | A `STOP` older than six hours on first connect is history, not a command. |
| **Command ack** | 1 per command | The single exempt message; still counts against volume so ack-loops cannot spam. |

Contacts are isolated: Karim's burst never costs Ali a token. All numbers are
injected-clock deterministic and covered by `tests_bridge/test_limiter.py`.

> **A person who said STOP is never messaged again until they explicitly
> resume.** This is checked before the limiter, before urgency, and before the
> sandbox can touch their state.

---

## 5. Transports

`transport.py` defines one protocol (`send_text`, `fetch_inbound`,
`resolve_key`, `close`) with two implementations:

- **`FakeTransport`** — in-memory, scripted inbox, records every send. Used by
  all tests and the demo. `is_fake=True`.
- **`McpStdioTransport`** — launches the workspace MCP server over stdio and
  speaks MCP JSON-RPC: `initialize`, `notifications/initialized`, and
  `tools/call` for `send_message` and `list_messages`. Proven on the wire
  against a stub server in `tests_bridge/fake_mcp_server.py`.

The real server is registered in this workspace as MCP `whatsapp`; its
launch command is configuration, not code:

```
WHATSAPP_REST_PORT=18656  <mcp-server-venv>/bin/python <whatsapp-mcp>/whatsapp-mcp-server/main.py
```

Inbound polling calls `list_messages(chat_jid=..., after=..., include_context=False)`
per mirrored 1:1 chat and parses the upstream's formatted text defensively (a
line that does not parse is dropped, never guessed). The bridge's validation is
the second line of defence.

Known upstream limitations, recorded honestly:
- `send_message` returns only `{success, message}` — no message id, so the
  adapter synthesises a stable-shaped id.
- `list_messages` returns *formatted text*, not JSON — parsed leniently.
- There is no push webhook in the upstream; inbound is polled. A poll interval
  of 5–15 s is expected. Commands are applied on the poll boundary, so
  `STOP` latency is bounded by that interval (still seconds; acceptable).

---

## 6. What is simulated vs real — stated, not implied

| Thing | Sandbox | Real bridge |
|-------|---------|-------------|
| Who is behind "Karim" | an AI character | a contact an operator explicitly mapped |
| How many WhatsApp accounts | 0 | **1 linked account** |
| `transport.is_fake` | `True` | `False` |
| `BridgeStatus.mode` | `dry_run` | `live` |
| `BridgeStatus.sandbox` | `true` | `false` only when real contacts are mapped |

The three AI neighbours **cannot each be a real number** — there is one linked
account. In a mixed run, a neighbour with `has_real_wire=False` is refused with
`simulated_identity`; it is never silently described as a real person. The UI's
badge reads `BridgeStatus`, so the demo cannot claim more than the bridge is
doing.

---

## 7. What a real send would require (the gate)

Nothing in the repo can send to a real number as shipped:

1. `BridgeConfig.dry_run=True` **and** `allow_live_sends=False`. Either one
   alone keeps the bridge dry (`effective_dry_run()` fails closed). A
   non-fake transport passed while dry is **replaced by the fake** with a
   warning — a wiring mistake cannot cause a real send.
2. **Owner go-ahead.** A live send additionally needs all of:
   - the MCP `whatsapp` server running with a **linked account** (QR pair), and
   - the operator to set `dry_run=False, allow_live_sends=True` and pass a
     `McpStdioTransport`, and
   - an explicit, named test contact who has agreed to be messaged, and
   - a **single** supervised message first, read back from the phone before any
     batch.
3. **Consent + content rules** for that first message: it must introduce
   NearMind and the STOP/BUSY commands, and must be sent to the owner's own
   number or a consenting neighbour — never a scraped contact list.
4. **Secrets** never live in the repo: the linked account is the MCP server's
   session, the OpenAI key stays in agent env. Phone numbers live only in the
   runtime contact map, never in code, issues or comments.

Until 1–4 are satisfied, the answer to "can NearMind message a real person?" is
**no**, and the bridge says so in `report().mode`.

---

## 8. How it was tested

```
./bridge/run_tests.sh          # or: python3 -m pytest tests_bridge -q
# 132 passed; no network, no account, no key
```

| File | Proves |
|------|--------|
| `test_commands.py` | STOP/BUSY/RESUME across case, punctuation, typos, durations; prose is not a command; parsing never raises. |
| `test_availability.py` | sticky STOP across 30 days; BUSY expiry at the exact second; idempotence and preserved `since`; STOP beats busy; **BUSY cannot weaken a sticky STOP**; RESUME; timed STOP; sandbox cannot override a real STOP; unavailable neighbours unreachable; `asleep` blocks. |
| `test_limiter.py` | burst boundary exact; daily cap holds over a 24 h drip; silence backoff doubles then refuses; duplicate suppressed; per-contact isolation. |
| `test_inbound_schema.py` | every malformed shape → typed failure, never an exception; unknown sender cannot STOP; replay rejected; huge body refused; control chars stripped. |
| `test_bridge_e2e.py` | the facade end to end on `FakeTransport`: STOP silences all future sends **including urgent**; `BUSY` after `STOP` keeps the person stopped; BUSY expires and messaging resumes; urgent overrides busy but not STOP; out-of-building never reached; ack exempt from limits; malformed inbound does not corrupt state; transport failure → `FAILED`; junk items don't abort a poll. |
| `test_mcp_adapter.py` | the real MCP adapter over stdio JSON-RPC against a stub: right tool + args; formatted-text parsing; dedupe; failure surfaces as `TransportError`. |

No real send happens in any test. `FakeTransport` is the only transport the
suite uses except `test_mcp_adapter.py`, which talks to a local stub, not
WhatsApp.

---

## 9. Integration notes for the backend (automation-eng-1)

I did not touch backend or frontend files; this module lives entirely under
`bridge/` with its tests in `tests_bridge/`. To wire it in:

- Build the contact map from config: `{neighbour_id: ContactRef(id, display_name)}`.
  Wire keys come from the runtime, **never from code**.
- Call `bridge.receive()` on a timer (5–15 s) or before each request; append
  `events`/`failures` to the decision log.
- Call `bridge.may_contact(neighbour_id, asleep=...)` in `eligibility.py` and
  put the returned reason straight into the decision log.
- Call `bridge.send(...)` and map `outcome`:
  `SENT` → thread message; `SUPPRESSED` → decision with `reason`; `REFUSED` →
  decision + schedule `retry_after`; `FAILED` → retry policy.
- `bridge.availability.snapshot(id)` already returns the exact inspector shape
  from the UI contract (`state`, `reason`, `since`, `source`).
