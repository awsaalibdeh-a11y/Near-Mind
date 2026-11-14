# NearMind HTTP API

Base URL: `http://localhost:5055/api` (override with `PORT`).

Run it:

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

The fake model is the default, so **no API key and no network are needed**.
The live contract is always served at `GET /api/contract`.

---

## Envelope

Every response — success or failure — uses the same envelope. Build one parser.

```json
{ "ok": true,  "data": { }, "error": null }
```

```json
{
  "ok": false,
  "data": null,
  "error": { "code": "reason_required", "message": "…", "details": {} }
}
```

Never branch on HTTP status alone; branch on `error.code`.

---

## Enums

| Name | Values |
| --- | --- |
| `availability` | `available`, `busy`, `not_at_home` |
| `urgency` | `low`, `high`, `emergency` |
| `safe(asleep)` | boolean, *independent of availability* |
| `offer_status` | `proposed`, `declined`, `vetoed`, `released`, `accepted` |
| `handover_state` | `proposed`, `agreed`, `collected`, `released`, `expired` |
| `request_status` | `parsed`, `outreach`, `awaiting_choice`, `awaiting_pickup`, `fulfilled`, `no_match`, `cancelled` |
| `safety_status` | `safe`, `unsafe`, `needs_check`, `unassessed` |
| `log_action` | see `GET /api/contract` → `enums.log_action` |

**Availability × sleep.** A neighbour's window state is
`availability.state` **plus** the boolean `asleep`. The four visible states:

| Window state | How to derive |
| --- | --- |
| available (lit) | `availability.state == "available" && !asleep` |
| busy (occupied) | `availability.state == "busy"` |
| not at home (vacant) | `availability.state == "not_at_home"` |
| asleep (dark) | `asleep == true` |

`availability` also carries `reason`, `since`, `set_by`, `expires_at`.

---

## Endpoints

### `GET /health`
`{ status, clock, mode, neighbours }` — `mode` is `"fake"` or `"openai"`.

### `GET /state`
`{ clock, now, maryam, neighbours[], stats }`

### `GET /neighbours`
Array of neighbour views (see **Neighbour shape**).

### `GET /neighbours/<id>`
Neighbour view plus `balance` (ledger).

**Neighbour shape**

```json
{
  "id": "karim",
  "house_number": "12",
  "name": "Karim",
  "personality": "…",
  "texting_style": "…",
  "availability": { "state": "available", "reason": "…", "since": "…", "set_by": "sandbox", "expires_at": null },
  "asleep": false,
  "sleep_window": ["23:00", "06:30"],
  "local_time": "19:00",
  "fairness_score": 0.5,
  "inventory": [{ "item": "ladder", "quantity": 1, "unit": "pcs", "condition": "creaky", "tags": [], "attributes": { "stability": "creaky" } }],
  "memory": [{ "at": "…", "note": "…" }],
  "is_real": false
}
```

### `POST /neighbours/<id>/availability`
The bridge hook. Body:

```json
{ "state": "busy", "reason": "on a call with my sister", "minutes": 30, "set_by": "whatsapp" }
```

* `reason` is **required** → `422 reason_required`.
* `state` must be an enum value → `422 invalid_state`.
* `busy` **requires `minutes`** so it expires on its own → `422 busy_needs_window`.
* `not_at_home` and `available` hold until changed (this is `STOP`).

### `POST /clock`
Demo control. Body: `{ "advance_minutes": 21 }` or `{ "set": "2026-11-14T02:05:00" }`.
Returns `{ clock, now, expiry_outcomes }`. Expiry rules fire during the move.

### `POST /chat`
The whole flow in one call. Body `{ "message": "anyone have salt?" }`.

```json
{
  "request": { "id": "req_…", "intent": { "item": "salt", "quantity": 2, "unit": "kg", "urgency": "low", "substitutes": [] }, "status": "awaiting_choice", "closure": null },
  "offers": [ { "id": "offer_…", "neighbour_id": "karim", "item": "salt", "quantity": 1, "unit": "kg", "condition": "good", "safety": { "status": "safe", "reason": "…", "hazards": [] }, "terms": "…", "score": 1.06, "reason": "…" } ],
  "recommendation": { "offer_id": "offer_…", "summary": "…", "reason": "…" },
  "closure": null,
  "skipped": [ { "neighbour_id": "ali", "reason": "Ali (#8) has neither salt nor an acceptable substitute (none offered)." } ],
  "schema_failures": []
}
```

If nothing is safe/reachable, `offers` is `[]`, `recommendation` is `null`, and
`closure` carries the message to show Maryam.

### `GET /requests/<id>`
`{ request, offers, threads, handovers, logs }` — the split view's data source.
Threads are **per neighbour and isolated**.

### `POST /requests/<id>/choose`
Body `{ "offer_id": "offer_…" }`.

```json
{ "handover": { "id": "ho_…", "state": "proposed", "expires_at": "…" },
  "released": [ { "neighbour_id": "ali", "thread_message": "…", "standby": true } ] }
```

* Vetoed offers are rejected → `422 cannot_choose_offer`.
* Everyone else is released politely; the runner-up is told it is on standby.

### `GET /handovers`, `GET /handovers/<id>`
Handover objects with `history`, `expires_at`, `checked_back_at`.

### `POST /handovers/<id>/agree`
`proposed → agreed`. Body `{ "note": "…" }` optional.

### `POST /handovers/<id>/complete`
`→ collected → released`, increments fairness, writes the ledger entry, marks
the request `fulfilled`. Returns `{ handover, ledger }`.

### `POST /handovers/sweep`
Run the expiry sweep: check back once, then pivot or close. Returns
`{ outcomes: [{ handover, action: "checked_back" | "pivoted" | "closed" }] }`.

### `GET /logs?request_id=&action=&limit=`
Decision logs, newest last. Each has a mandatory non-empty `reason`.

### `GET /ledger`
`{ entries, balance, reciprocity }`.

### `POST /ledger/<entry_id>/settle`
Mark one debt settled.

### `POST /ledger/reciprocity`
Body `{ "neighbour_id": "karim", "accepted": true, "item": "sugar" }`.
Maryam's explicit answer. Declining changes nothing.

### `POST /inbound/reverse-request`
Body `{ "neighbour_id": "karim", "item": "sugar" }` → `{ route_to_maryam_first, reason, suggestion }`.
Suggest only; nothing is routed until she confirms.

### `GET /dashboard`
`{ stats, clock, balance, reciprocity, open_handovers, recent_logs }`

### `GET /digest`
`{ lines: ["…"], clock }`

### `GET /export`
Every thread verbatim, with translations alongside.

### `GET /scenarios`, `POST /scenarios/<id>/run`
Scenario ids: `safety_veto`, `urgency_low_2am`, `urgency_high_2am`,
`availability_routing`, `busy_holder`, `handover_expiry_pivot`, `reciprocity`.

---

## Error codes

| Code | Status | Meaning |
| --- | --- | --- |
| `message_required` | 422 | empty chat message |
| `reason_required` | 422 | availability change without a reason |
| `invalid_state` | 422 | not a valid availability value |
| `busy_needs_window` | 422 | busy without `minutes` |
| `invalid_minutes` / `invalid_time` / `missing_time` | 422 | clock body |
| `offer_required` / `not_found` | 422 / 404 | choosing an offer |
| `cannot_choose_offer` | 422 | vetoed offer, or wrong request |
| `invalid_transition` | 409 | illegal handover transition |
| `internal_error` | 500 | unexpected; nothing persisted |

---

## For the WhatsApp bridge

1. `STOP` → `POST /neighbours/<id>/availability` with `state: "not_at_home"`,
   `reason: "STOP requested via WhatsApp"`, `set_by: "whatsapp"`.
2. `BUSY` → same with `state: "busy"`, `minutes: <window>`, `set_by: "whatsapp"`.
3. A reverse request from a neighbour → `POST /inbound/reverse-request`.
4. A neighbour's reply during an active request should be translated through
   the same schema path; the bridge must post it as a thread message, never
   mutate offers directly.

Rate limiting and the MCP transport live in the bridge, not here.
