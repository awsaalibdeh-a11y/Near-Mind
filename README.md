# NearMind

An AI agent for a neighbourhood. Maryam (#10) messages it for a small favour —
"anyone have salt?", "I need a ladder for a smoke detector". NearMind works out
quantity, urgency and acceptable substitutes, messages the right neighbours
privately (each in their own style), handles the back-and-forth, flags safety
issues, relays offers with a recommendation, arranges the handover, and
politely releases everyone else.

Three AI neighbours live in a sandbox — **Karim**, **Ali**, and a third defined
at build time (read from config, never hard-coded). The sandbox is the test
bench for social edge cases; a WhatsApp bridge proves the same logic works with
real people.

This repository currently contains **the backend** (`nearmind/`, `tests/`).
The UI and WhatsApp bridge are separate surfaces that consume the contract in
[`docs/API.md`](docs/API.md).

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py       # http://localhost:5055
```

```bash
curl -s localhost:5055/api/health
curl -s -X POST localhost:5055/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"anyone have salt?"}' | python3 -m json.tool
```

No API key and no network needed: the deterministic fake model is the default.
To use `gpt-5-mini`:

```bash
export OPENAI_API_KEY=sk-...
export NEARMIND_FAKE_MODEL=0
```

## Configuration

| Env var | Default | Meaning |
| --- | --- | --- |
| `NEARMIND_FAKE_MODEL` | `1` | `0` uses the live OpenAI model |
| `NEARMIND_MODEL` | `gpt-5-mini` | model name |
| `OPENAI_API_KEY` | — | required only for the live model |
| `NEARMIND_THIRD_NAME` | `Umm Samir` | the third neighbour's name |
| `NEARMIND_HANDOVER_MINUTES` | `20` | handover expiry (clamped to 15–30) |
| `NEARMIND_START` | `2026-11-14T19:00` | virtual clock start |
| `PORT` | `5055` | HTTP port |

No secrets are stored in the repo.

## Architecture

```
nearmind/
  models.py         pydantic domain models; DecisionLog requires a reason
  config.py         settings + the neighbour seed (stock, personalities, sleep)
  clock.py          virtual clock; per-neighbour clock offsets
  world.py          mutable state: neighbours, availability, threads, ledger, logs
  eligibility.py    who may be contacted and why — runs before any outreach
  safety.py         deterministic veto rules, layered over the model's verdict
  schemas.py        strict model-output schemas + narrow, non-inventing repair
  llm.py            FakeModel, OpenAIModel, FailingModel, ValidatingModel
  agent.py          the flow: parse → eligibility → outreach → offers → handover
  handover.py       state machine + expiry sweep (check back, then pivot)
  ledger.py         two-way favour ledger + reciprocity routing (suggest only)
  scenarios.py      scripted showcase scenarios, deterministic
  api.py            Flask app + the HTTP contract
tests/              85 tests; run with `.venv/bin/python -m pytest`
docs/API.md         the contract the UI and bridge build against
```

### Design rules

**Every model call is schema-validated.** A malformed or off-script reply is
never applied to state. The worst it can do is force a clarifying question or a
conservative fallback. Inventing a quantity is how a ledger gets corrupted, so
the validator never invents semantics — it only strips fences, extracts the
first JSON object, and coerces unambiguous scalars.

**The reason is mandatory.** A `DecisionLog` without a non-empty reason is
rejected at construction. Logs read like
`Skipped Umm Samir: local time 02:05, sleep window 21:30–05:30. Salt is not urgent.`

**Availability is checked before outreach.** Out-of-building neighbours are
never contacted. Busy neighbours are routed around unless urgency is
`emergency`. Sleeping neighbours are skipped unless urgency is `high` or
`emergency`, and the wake is logged as a deliberate override.

**The veto holds under scarcity.** An unsafe item is never recommended, even
when it is the only one. The model may propose "safe"; the deterministic rules
in `safety.py` can only tighten a verdict, never loosen it.

**Maryam is never left waiting.** Every handover has a 15–30 minute expiry. On
first expiry NearMind checks back and extends; on second expiry it pivots to the
runner-up (kept on standby for exactly this reason) or closes honestly.

**Reciprocity is suggested, never forced.** When Maryam owes a neighbour, that
neighbour's reverse requests are prioritised — but only after she confirms.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Coverage includes availability gating, the safety veto under scarcity, the
urgency override pair at 02:00, no-match closure, handover expiry → pivot,
reciprocity routing, and schema-failure degradation.

The safety-veto tests are proven able to fail: with `safety.tighten()` neutered,
four tests go red, including `test_veto_holds_even_when_it_is_the_only_ladder`.
That regression check is itself a test
(`test_veto_test_fails_when_veto_removed`), so the proof runs on every CI build.

## Showcase scenarios

`POST /api/scenarios/<id>/run` replays these deterministically:

| id | what it proves |
| --- | --- |
| `safety_veto` | Creaky ladder rejected; nobody has a replacement; the veto holds |
| `urgency_low_2am` | Salt at 02:00 — nobody is woken; closure names substitutes |
| `urgency_high_2am` | A leak at 02:00 — a neighbour is woken, logged as an override |
| `availability_routing` | The obvious holder is out; NearMind never contacts them |
| `busy_holder` | The only holder is busy; NearMind does not barge in |
| `handover_expiry_pivot` | "Give me 5" then silence → check back → pivot to Ali |
| `reciprocity` | Two debts to Karim prioritise his reverse request |
