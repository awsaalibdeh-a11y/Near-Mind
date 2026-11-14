# NearMind — build plan

NearMind is an AI agent for a neighbourhood. Maryam (#10) messages it for a small
favour; it works out quantity, urgency and acceptable substitutes, messages the right
neighbours privately (each in their own style), handles the back-and-forth, flags
safety issues, relays offers with a recommendation, arranges the handover and
politely releases everyone else.

Three AI neighbours live in a sandbox (Karim, Ali, and a third defined at build time —
its name is read from config, never hard-coded). The sandbox is the test bench; the
WhatsApp bridge is the proof the same logic works with real people.

## Ownership map

| Area | Owner | Paths |
| --- | --- | --- |
| Backend, domain model, agent flow, schemas, HTTP API | automation-eng-1 | `nearmind/`, `tests/`, `requirements.txt` |
| WhatsApp bridge (MCP adapter) | nearmind-whatsapp-engineer | `bridge/` (not in this repo yet) |
| Frontend shell + visual system | ui-builder-1 / nearmind-ui-engineer | `frontend/` (not in this repo yet) |
| Remotion stage internals | automation-eng-1 (LEG-437) | `frontend/src/remotion/` |

The backend is the only thing in this repo today. Everything else is a consumer of
the HTTP contract in `docs/API.md`.

## Layout

```
nearmind/
  __init__.py          app factory, one-command runner
  config.py            env + sandbox seed (neighbours, stock, sleep windows)
  models.py            domain models (pydantic) — the single source of truth
  schemas.py           strict model-output schemas + lenient repair
  llm.py               LLM protocol, FailingModel, FakeModel, OpenAIModel
  clock.py             virtual clock (scriptable, deterministic)
  availability.py      availability state machine + STOP/BUSY + sleep interaction
  world.py             neighbourhood world: clock, neighbours, ledger, threads, logs
  safety.py            safety assessment + veto rules
  eligibility.py       who may be contacted, and why (or why not)
  ledger.py            favour ledger + reciprocity routing
  handover.py          handover state machine + expiry sweep
  agent.py             the flow: parse → eligibility → outreach → offers → handover
  scenarios.py         scripted showcase scenarios (safety veto, urgency, availability)
  api.py               Flask blueprint + envelope + error handling
tests/
  test_*.py
docs/
  API.md               the contract the UI and bridge build against
```

## Non-negotiables

1. **Every model call is schema-validated.** A malformed or off-script reply is
   repaired where possible, downgraded where not, and never mutates ledger,
   inventory or stats. Failed parses are recorded as decision logs with a reason.
2. **The reason is mandatory.** A `DecisionLog` without a non-empty `reason` is
   rejected by the API with a 422 and by the pydantic model at construction.
3. **Availability is checked before outreach.** Out-of-building neighbours are never
   contacted — not even "softly". Busy neighbours are routed around unless urgency
   is `emergency`, and even then the log says why.
4. **The safety veto holds under scarcity.** An unsafe item is never recommended,
   regardless of whether an alternative exists.
5. **Sleep is respected unless urgency overrides it deliberately.** A `high` or
   `emergency` request at 02:00 may wake someone, but the log records the decision
   as an explicit override with the reason.
6. **The fake model is fully deterministic.** No API key, no network, no clock
   surprises. The showcase and the tests both depend on it.
7. **No secrets in the repo.** The OpenAI key arrives via `OPENAI_API_KEY`.

## Flow

```
message ──► parse (schema)  ──►  intent: item, qty, urgency, substitutes, attrs
                │
                ▼
        eligibility filter  ──►  per-neighbour verdict + reason (logged)
                │
                ▼
        outreach (per-neighbour style, isolated thread)
                │
                ▼
        reply translation  ──►  clarify (short question) → re-read
                │
                ▼
        safety assessment  ──►  veto / pass / needs-condition
                │
                ▼
        offers + recommendation  ──►  Maryam chooses
                │
                ├──► handover: proposed → agreed → collected → released
                │        (15–30 min expiry → check-back or pivot)
                └──► no match: closure with local substitutes
```

## Status

Backend scope of LEG-434 is implemented and tested. `pytest` is green against the
fake model and needs no network.
