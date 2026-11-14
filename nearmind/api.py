"""Flask API — the contract the UI and the WhatsApp bridge build against.

Every response is an envelope:

    {"ok": true,  "data": {...}, "error": null}
    {"ok": false, "data": null,  "error": {"code": "...", "message": "...", "details": {...}}}

The envelope never varies. That is what lets the UI have one error path and
the bridge one parser.
"""

from __future__ import annotations

from dataclasses import dataclass

from flask import Blueprint, Flask, current_app, jsonify, request

from .agent import Agent
from .config import Settings
from .handover import InvalidTransition, sweep
from .ledger import (
    balance,
    confirm_reciprocity,
    reciprocity_suggestions,
    route_inbound,
)
from .llm import FakeModel, OpenAIModel
from .models import Availability, LedgerDirection, LogAction, ReciprocitySuggestion
from .scenarios import SCENARIOS
from .world import World


# --------------------------------------------------------------------------- #
# Envelope
# --------------------------------------------------------------------------- #


def ok(data=None, status: int = 200):
    return jsonify({"ok": True, "data": data, "error": None}), status


def fail(code: str, message: str, status: int = 400, details: dict | None = None):
    return (
        jsonify(
            {
                "ok": False,
                "data": None,
                "error": {"code": code, "message": message, "details": details or {}},
            }
        ),
        status,
    )


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #


@dataclass
class AppState:
    world: World
    model: object
    settings: Settings

    def agent(self) -> Agent:
        return Agent(self.world, self.model)


def create_app(settings: Settings | None = None, model=None) -> Flask:
    settings = settings or Settings()
    app = Flask(__name__)

    if model is None:
        if settings.use_fake_model or not settings.openai_api_key:
            model = FakeModel()
        else:
            model = OpenAIModel(settings.openai_api_key, settings.model_name)

    app.extensions["nearmind"] = AppState(
        world=World.sandbox(settings), model=model, settings=settings
    )

    @app.errorhandler(ApiError)
    def _handle_api_error(exc: ApiError):
        return fail(exc.code, exc.message, exc.status, exc.details)

    @app.errorhandler(404)
    def _handle_404(_exc):
        return fail("not_found", "No such endpoint.", 404)

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception):
        app.logger.exception("unhandled error")
        return fail(
            "internal_error",
            "Something went wrong inside NearMind. Nothing was saved.",
            500,
            {"type": type(exc).__name__},
        )

    app.register_blueprint(api)

    @app.get("/")
    def index():
        return ok({"service": "NearMind", "version": "1.0", "docs": "/api/contract"})

    return app


def state() -> AppState:
    return current_app.extensions["nearmind"]


def world() -> World:
    return state().world


api = Blueprint("nearmind_api", __name__, url_prefix="/api")


# --------------------------------------------------------------------------- #
# Sandbox / health
# --------------------------------------------------------------------------- #


@api.get("/health")
def health():
    w = world()
    return ok(
        {
            "status": "ok",
            "clock": w.clock.hhmm(),
            "mode": "fake" if isinstance(state().model, FakeModel) else "openai",
            "neighbours": len(w.neighbours),
        }
    )


@api.get("/contract")
def contract():
    return ok(CONTRACT)


@api.get("/state")
def get_state():
    return ok(world().snapshot())


@api.get("/neighbours")
def list_neighbours():
    w = world()
    return ok([w.neighbour_view(nid) for nid in w.neighbours])


@api.get("/neighbours/<neighbour_id>")
def get_neighbour(neighbour_id: str):
    w = world()
    if neighbour_id not in w.neighbours:
        raise ApiError("not_found", f"No neighbour {neighbour_id!r}.", 404)
    view = w.neighbour_view(neighbour_id)
    view["balance"] = balance(w)[neighbour_id]
    view["reciprocity_owed_by_maryam"] = balance(w)[neighbour_id]["maryam_owes"]
    return ok(view)


@api.post("/neighbours/<neighbour_id>/availability")
def set_availability(neighbour_id: str):
    """Sandbox/WhatsApp entry point for availability. This is the bridge hook."""
    w = world()
    if neighbour_id not in w.neighbours:
        raise ApiError("not_found", f"No neighbour {neighbour_id!r}.", 404)
    body = request.get_json(silent=True) or {}
    raw_state = body.get("state")
    reason = (body.get("reason") or "").strip()
    if not reason:
        raise ApiError("reason_required", "Availability changes must carry a reason.", 422)
    try:
        avail = Availability(raw_state)
    except ValueError:
        raise ApiError(
            "invalid_state",
            "state must be one of: available, busy, not_at_home.",
            422,
        )
    minutes = body.get("minutes")
    if minutes is not None and not isinstance(minutes, int):
        raise ApiError("invalid_minutes", "minutes must be an integer.", 422)
    if avail is Availability.BUSY and not minutes:
        # A busy window must expire on its own; that is the anti-stuck guarantee.
        raise ApiError(
            "busy_needs_window",
            "A busy state needs a minutes value so it expires on its own.",
            422,
        )
    result = w.set_availability(
        neighbour_id,
        avail,
        reason,
        set_by=body.get("set_by", "sandbox"),
        minutes=minutes,
    )
    return ok(result.model_dump(mode="json"))


@api.post("/clock")
def set_clock():
    """Advance (or set) the virtual clock. Expiry rules fire on the way."""
    w = world()
    body = request.get_json(silent=True) or {}
    if "advance_minutes" in body:
        try:
            minutes = int(body["advance_minutes"])
        except (TypeError, ValueError):
            raise ApiError("invalid_minutes", "advance_minutes must be an integer.", 422)
        w.tick(minutes)
    elif "set" in body:
        try:
            from datetime import datetime

            w.clock.set(datetime.fromisoformat(body["set"]))
        except ValueError:
            raise ApiError("invalid_time", "set must be an ISO-8601 datetime.", 422)
    else:
        raise ApiError("missing_time", "Send advance_minutes or set.", 422)
    outcomes = sweep(w)
    return ok({"clock": w.clock.hhmm(), "now": w.now().isoformat(), "expiry_outcomes": outcomes})


# --------------------------------------------------------------------------- #
# Chat / requests
# --------------------------------------------------------------------------- #


@api.post("/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        raise ApiError("message_required", "Send a non-empty message.", 422)
    agent = state().agent()
    result = agent.handle(message)
    return ok(result.to_dict())


@api.get("/requests/<request_id>")
def get_request(request_id: str):
    w = world()
    req = w.requests.get(request_id)
    if req is None:
        raise ApiError("not_found", f"No request {request_id!r}.", 404)
    offers = [o.model_dump(mode="json") for o in w.offers.values() if o.request_id == request_id]
    threads = [
        {
            "id": t.id,
            "neighbour_id": t.neighbour_id,
            "messages": [m.model_dump(mode="json") for m in t.messages],
        }
        for t in w.threads_for(request_id)
    ]
    handovers = [
        h.model_dump(mode="json") for h in w.handovers.values() if h.request_id == request_id
    ]
    return ok(
        {
            "request": req.model_dump(mode="json"),
            "offers": offers,
            "threads": threads,
            "handovers": handovers,
            "logs": [
                l.model_dump(mode="json") for l in w.logs if l.request_id == request_id
            ],
        }
    )


@api.get("/requests")
def list_requests():
    w = world()
    return ok([r.model_dump(mode="json") for r in w.requests.values()])


@api.post("/requests/<request_id>/choose")
def choose(request_id: str):
    w = world()
    if request_id not in w.requests:
        raise ApiError("not_found", f"No request {request_id!r}.", 404)
    body = request.get_json(silent=True) or {}
    offer_id = body.get("offer_id")
    if not offer_id:
        raise ApiError("offer_required", "Send offer_id.", 422)
    if offer_id not in w.offers:
        raise ApiError("not_found", f"No offer {offer_id!r}.", 404)
    try:
        result = state().agent().choose(request_id, offer_id)
    except ValueError as exc:
        raise ApiError("cannot_choose_offer", str(exc), 422)
    return ok(result)


# --------------------------------------------------------------------------- #
# Handovers
# --------------------------------------------------------------------------- #


@api.get("/handovers")
def list_handovers():
    w = world()
    return ok([h.model_dump(mode="json") for h in w.handovers.values()])


@api.get("/handovers/<handover_id>")
def get_handover(handover_id: str):
    w = world()
    h = w.handovers.get(handover_id)
    if h is None:
        raise ApiError("not_found", f"No handover {handover_id!r}.", 404)
    return ok(h.model_dump(mode="json"))


@api.post("/handovers/<handover_id>/agree")
def agree_handover(handover_id: str):
    from .handover import agree

    w = world()
    h = w.handovers.get(handover_id)
    if h is None:
        raise ApiError("not_found", f"No handover {handover_id!r}.", 404)
    body = request.get_json(silent=True) or {}
    try:
        agree(w, h, when=body.get("note", ""))
    except InvalidTransition as exc:
        raise ApiError("invalid_transition", str(exc), 409)
    return ok(h.model_dump(mode="json"))


@api.post("/handovers/<handover_id>/complete")
def complete_handover(handover_id: str):
    w = world()
    if handover_id not in w.handovers:
        raise ApiError("not_found", f"No handover {handover_id!r}.", 404)
    if w.handovers[handover_id].state.value in ("collected", "released"):
        raise ApiError("invalid_transition", "This handover is already complete.", 409)
    try:
        return ok(state().agent().finish_handover(handover_id))
    except InvalidTransition as exc:
        raise ApiError("invalid_transition", str(exc), 409)


@api.post("/handovers/sweep")
def sweep_handovers():
    """Run the expiry sweep explicitly (the bridge / a scheduler can call this)."""
    return ok({"outcomes": sweep(world())})


# --------------------------------------------------------------------------- #
# Logs, ledger, dashboard
# --------------------------------------------------------------------------- #


@api.get("/logs")
def get_logs():
    w = world()
    request_id = request.args.get("request_id")
    action = request.args.get("action")
    limit = min(int(request.args.get("limit", 200)), 1000)
    logs = list(w.logs)
    if request_id:
        logs = [l for l in logs if l.request_id == request_id]
    if action:
        logs = [l for l in logs if l.action.value == action]
    return ok([l.model_dump(mode="json") for l in logs[-limit:]])


@api.get("/ledger")
def get_ledger():
    w = world()
    return ok(
        {
            "entries": [e.model_dump(mode="json") for e in w.ledger],
            "balance": balance(w),
            "reciprocity": [s.model_dump(mode="json") for s in reciprocity_suggestions(w)],
        }
    )


@api.post("/ledger/<entry_id>/settle")
def settle_ledger(entry_id: str):
    w = world()
    entry = w.settle_ledger(entry_id)
    if entry is None:
        raise ApiError("not_found", "No open ledger entry with that id.", 404)
    return ok(entry.model_dump(mode="json"))


@api.post("/ledger/reciprocity")
def reciprocity_decision():
    """Maryam confirms or declines a reciprocity nudge. Never applied unasked."""
    w = world()
    body = request.get_json(silent=True) or {}
    neighbour_id = body.get("neighbour_id")
    if neighbour_id not in w.neighbours:
        raise ApiError("not_found", f"No neighbour {neighbour_id!r}.", 404)
    accepted = bool(body.get("accepted"))
    item = body.get("item") or "a favour"
    suggestion = ReciprocitySuggestion(
        neighbour_id=neighbour_id,
        direction=LedgerDirection.MARYAM_OWES,
        open_count=max(1, balance(w)[neighbour_id]["maryam_owes"]),
        summary="reciprocity decision",
        reason="Maryam was shown the nudge and answered it.",
    )
    try:
        result = confirm_reciprocity(w, suggestion, accepted=accepted, item=item)
    except ValueError as exc:
        raise ApiError("no_open_debt", str(exc), 409)
    return ok({"result": result, "balance": balance(w)})


@api.post("/inbound/reverse-request")
def reverse_request():
    """A neighbour asks Maryam for something. Route through the ledger."""
    w = world()
    body = request.get_json(silent=True) or {}
    neighbour_id = body.get("neighbour_id")
    item = (body.get("item") or "").strip()
    if neighbour_id not in w.neighbours:
        raise ApiError("not_found", f"No neighbour {neighbour_id!r}.", 404)
    if not item:
        raise ApiError("item_required", "Send item.", 422)
    route, reason, suggestion = route_inbound(w, neighbour_id, item)
    return ok(
        {
            "route_to_maryam_first": route,
            "reason": reason,
            "suggestion": suggestion.model_dump(mode="json") if suggestion else None,
        }
    )


@api.get("/dashboard")
def dashboard():
    w = world()
    return ok(
        {
            "stats": dict(w.stats),
            "clock": w.clock.hhmm(),
            "balance": balance(w),
            "reciprocity": [s.model_dump(mode="json") for s in reciprocity_suggestions(w)],
            "open_handovers": [
                h.model_dump(mode="json") for h in w.handovers.values() if h.is_open
            ],
            "recent_logs": [l.model_dump(mode="json") for l in w.logs[-30:]],
        }
    )


@api.get("/digest")
def digest():
    """A short human-readable summary for the daily digest panel."""
    w = world()
    lines = []
    if w.stats["requests"] == 0:
        lines.append("No favours asked yet today.")
    else:
        lines.append(
            f"{w.stats['requests']} favour{'s' if w.stats['requests'] != 1 else ''} asked, "
            f"{w.stats['fulfilled']} fulfilled, {w.stats['no_match']} closed with no match."
        )
    for nid, counts in balance(w).items():
        if counts["maryam_owes"]:
            lines.append(
                f"Maryam owes {w.neighbour(nid).name} {counts['maryam_owes']} favour{'s' if counts['maryam_owes'] != 1 else ''}."
            )
    if w.stats["vetoed"]:
        lines.append(
            f"{w.stats['vetoed']} item{'s' if w.stats['vetoed'] != 1 else ''} turned down on safety grounds."
        )
    return ok({"lines": lines, "clock": w.clock.hhmm()})


@api.get("/export")
def export():
    """Conversation export: every isolated thread, verbatim, plus translations."""
    w = world()
    return ok(
        {
            "exported_at": w.now().isoformat(),
            "threads": [
                {
                    "request_id": t.request_id,
                    "neighbour": w.neighbour(t.neighbour_id).name,
                    "messages": [
                        {
                            "role": m.role.value,
                            "at": m.at.isoformat(),
                            "text": m.text,
                            "translated": m.translated,
                        }
                        for m in t.messages
                    ],
                }
                for t in w.threads.values()
            ],
        }
    )


# --------------------------------------------------------------------------- #
# Showcase
# --------------------------------------------------------------------------- #


@api.get("/scenarios")
def list_scenarios():
    return ok(
        [
            {"id": key, "title": s["title"], "description": s["description"]}
            for key, s in SCENARIOS.items()
        ]
    )


@api.post("/scenarios/<scenario_id>/run")
def run_scenario(scenario_id: str):
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        raise ApiError("not_found", f"No scenario {scenario_id!r}.", 404)
    return ok({"id": scenario_id, **scenario["fn"]()})


# --------------------------------------------------------------------------- #
# Contract (served so the UI never has to ask)
# --------------------------------------------------------------------------- #

CONTRACT = {
    "envelope": {
        "ok": True,
        "data": "object | array | null",
        "error": None,
    },
    "error_envelope": {
        "ok": False,
        "data": None,
        "error": {"code": "string", "message": "string", "details": {}},
    },
    "endpoints": [
        {"method": "GET", "path": "/api/health", "desc": "Liveness, clock, model mode."},
        {"method": "GET", "path": "/api/state", "desc": "Clock, neighbours, stats."},
        {"method": "GET", "path": "/api/neighbours", "desc": "All neighbours incl. availability, asleep, fairness, inventory."},
        {"method": "GET", "path": "/api/neighbours/<id>", "desc": "One neighbour + ledger balance."},
        {"method": "POST", "path": "/api/neighbours/<id>/availability",
         "desc": "Set availability. Body: {state, reason, minutes?, set_by?}. BUSY needs minutes.",
         "errors": ["reason_required", "invalid_state", "busy_needs_window"]},
        {"method": "POST", "path": "/api/clock",
         "desc": "Advance or set the virtual clock. Body: {advance_minutes} or {set}.",
         "errors": ["invalid_minutes", "invalid_time", "missing_time"]},
        {"method": "POST", "path": "/api/chat",
         "desc": "Run the whole agent flow. Body: {message}. Returns request, offers, recommendation, closure, skipped, schema_failures.",
         "errors": ["message_required"]},
        {"method": "GET", "path": "/api/requests/<id>", "desc": "Request + offers + threads + handovers + logs."},
        {"method": "POST", "path": "/api/requests/<id>/choose",
         "desc": "Body: {offer_id}. Opens a handover, releases others (runner-up on standby).",
         "errors": ["offer_required", "not_found", "cannot_choose_offer"]},
        {"method": "GET", "path": "/api/handovers", "desc": "All handovers."},
        {"method": "POST", "path": "/api/handovers/<id>/agree", "desc": "proposed → agreed. Body: {note?}."},
        {"method": "POST", "path": "/api/handovers/<id>/complete", "desc": "agreed → collected → released, writes one ledger entry."},
        {"method": "POST", "path": "/api/handovers/sweep", "desc": "Expire open handovers: check back, then pivot or close."},
        {"method": "GET", "path": "/api/logs", "desc": "Decision logs. Filters: request_id, action, limit."},
        {"method": "GET", "path": "/api/ledger", "desc": "Entries, balance, reciprocity suggestions."},
        {"method": "POST", "path": "/api/ledger/reciprocity",
         "desc": "Body: {neighbour_id, accepted, item}. Maryam's explicit answer to a nudge."},
        {"method": "POST", "path": "/api/inbound/reverse-request",
         "desc": "Body: {neighbour_id, item}. Whether to prioritise this request for Maryam."},
        {"method": "GET", "path": "/api/dashboard", "desc": "Stats, balance, reciprocity, open handovers, recent logs."},
        {"method": "GET", "path": "/api/digest", "desc": "Human-readable daily summary lines."},
        {"method": "GET", "path": "/api/export", "desc": "Verbatim conversation export, all threads."},
        {"method": "GET", "path": "/api/scenarios", "desc": "Showcase scenario list."},
        {"method": "POST", "path": "/api/scenarios/<id>/run", "desc": "Run a scenario deterministically."},
        {"method": "GET", "path": "/api/contract", "desc": "This document."},
    ],
    "enums": {
        "availability": ["available", "busy", "not_at_home"],
        "urgency": ["low", "high", "emergency"],
        "offer_status": ["proposed", "declined", "vetoed", "released", "accepted"],
        "handover_state": ["proposed", "agreed", "collected", "released", "expired"],
        "request_status": ["parsed", "outreach", "awaiting_choice", "awaiting_pickup", "fulfilled", "no_match", "cancelled"],
        "safety_status": ["safe", "unsafe", "needs_check", "unassessed"],
        "log_action": [a.value for a in LogAction],
    },
}


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #


def main() -> None:
    import os

    app = create_app()
    port = int(os.getenv("PORT", "5055"))
    app.run(host="0.0.0.0", port=port, debug=False)
