"""Scripted showcase scenarios.

Each scenario builds a fresh `World`, sets the clock and availability, optionally
scripts neighbour replies, and runs the flow. Deterministic: the same scenario
always produces the same logs, so the Showcase surface can replay it.

The three required demos:

* `safety_veto` — the only ladder in the building is creaky; the veto holds
  even though nobody else has one.
* `urgency_low_2am` — salt for dinner at 02:00; nobody is woken. Paired with
  `urgency_high_2am` — a leak at 02:00; a neighbour is deliberately woken and
  the wake is logged as an override.
* `availability_routing` — the obvious holder is out; NearMind routes around
  them without contacting them at all.
"""

from __future__ import annotations

from datetime import datetime

from .agent import Agent
from .config import Settings
from .llm import FakeModel
from .models import Availability, LedgerDirection
from .world import World


def _world(hour: int, minute: int = 0) -> World:
    settings = Settings(start_time=datetime(2026, 11, 14, hour, minute))
    world = World.sandbox(settings)
    world.reply_script = {}  # type: ignore[attr-defined]
    return world


def _run(world: World, message: str, model=None):
    agent = Agent(world, model or FakeModel())
    return agent.handle(message)


# --------------------------------------------------------------------------- #
# 1. Safety veto
# --------------------------------------------------------------------------- #


def safety_veto() -> dict:
    """Creaky ladder is the obvious answer. NearMind refuses it anyway."""
    world = _world(19, 0)
    # Make the two ladders the only ladders: Karim's is creaky, Umm Samir's is
    # missing a rung. Ali has a step ladder (a substitute), so remove it to
    # prove the veto holds *under scarcity* — and to distinguish the two ladders.
    world.neighbours["ali"].inventory = [
        inv for inv in world.neighbours["ali"].inventory if "ladder" not in inv.item
    ]
    world.set_availability("umm_samir", Availability.AVAILABLE, "At home, in the kitchen", set_by="sandbox")

    result = _run(world, "I need a ladder for a smoke detector, mine broke")
    return _pack(world, result)


# --------------------------------------------------------------------------- #
# 2. Urgency: low at 2 AM (respects sleep) vs high at 2 AM (wakes)
# --------------------------------------------------------------------------- #


def _set_2am(world: World) -> None:
    for nid in world.neighbours:
        world.set_availability(nid, Availability.AVAILABLE, "At home, asleep", set_by="sandbox")


def urgency_low_2am() -> dict:
    world = _world(2, 5)
    _set_2am(world)
    result = _run(world, "does anyone have salt? I want some for dinner")
    return _pack(world, result)


def urgency_high_2am() -> dict:
    world = _world(2, 5)
    _set_2am(world)
    result = _run(world, "URGENT the pipe under my sink is leaking badly, anyone have a drill or tools?")
    return _pack(world, result)


# --------------------------------------------------------------------------- #
# 3. Availability routing
# --------------------------------------------------------------------------- #


def availability_routing() -> dict:
    """Karim has the baking soda — but he's out. Route around him."""
    world = _world(19, 0)
    world.set_availability("karim", Availability.NOT_AT_HOME, "Out at the gym, back around 21:00", set_by="sandbox")
    world.reply_script = {  # type: ignore[attr-defined]
        ("ali", "baking soda"): "We have white vinegar and lemon juice. Both work for raising in baking.",
        ("umm_samir", "baking soda"): "habibti yes, the pink box... it's in the cupboard above the stove",
    }
    result = _run(world, "anyone have baking soda? I'm making a cake")
    return _pack(world, result)


def busy_holder() -> dict:
    """The only holder is busy. NearMind waits rather than barging in."""
    world = _world(19, 0)
    world.set_availability("karim", Availability.BUSY, "On a work call, until about 19:30", set_by="sandbox")
    result = _run(world, "does anyone have a drill? I need to put up a shelf")
    return _pack(world, result)


# --------------------------------------------------------------------------- #
# 4. Handover expiry → pivot
# --------------------------------------------------------------------------- #


def handover_expiry_pivot() -> dict:
    """Karim (best offer) goes quiet; NearMind checks back, then pivots to Ali."""
    world = _world(19, 0)
    # Give Ali salt so there is a genuine second-best offer to pivot to.
    from .models import InventoryItem

    world.neighbours["ali"].inventory.append(
        InventoryItem(item="salt", quantity=0.5, unit="kg", condition="good")
    )
    world.reply_script = {  # type: ignore[attr-defined]
        ("karim", "salt"): "yeah i've got some! give me 5 minutes",
    }
    agent = Agent(world, FakeModel())
    result = agent.handle("anyone have salt?")
    if not result.offers:
        return _pack(world, result)
    # Maryam picks the offer that is going to go quiet (Karim, who said "give me 5").
    karim_offer = next(o for o in result.offers if o.neighbour_id == "karim")
    agent.choose(result.request.id, karim_offer.id)
    world.tick(21)  # past the 20-minute expiry
    from .handover import sweep

    outcomes = sweep(world)
    world.tick(31)  # past the check-back extension
    outcomes += sweep(world)
    packed = _pack(world, result)
    packed["expiry_outcomes"] = outcomes
    return packed


# --------------------------------------------------------------------------- #
# 5. Reciprocity
# --------------------------------------------------------------------------- #


def reciprocity() -> dict:
    world = _world(19, 0)
    from .ledger import confirm_reciprocity, reciprocity_suggestions, route_inbound

    world.add_ledger(
        LedgerDirection.MARYAM_OWES,
        "karim",
        "drill",
    )
    world.add_ledger(
        LedgerDirection.MARYAM_OWES,
        "karim",
        "baking soda",
    )
    route, reason, suggestion = route_inbound(world, "karim", "sugar")
    if suggestion is not None:
        confirm_reciprocity(world, suggestion, accepted=True, item="sugar")
    return {
        "suggestions": [s.model_dump(mode="json") for s in reciprocity_suggestions(world)],
        "route_to_maryam_first": route,
        "reason": reason,
        "logs": [l.model_dump(mode="json") for l in world.logs],
    }


SCENARIOS: dict[str, dict] = {
    "safety_veto": {
        "title": "Safety veto under scarcity",
        "description": "The only ladder in the building is creaky. NearMind refuses it.",
        "fn": safety_veto,
    },
    "urgency_low_2am": {
        "title": "02:00 — low urgency respects sleep",
        "description": "Salt for dinner at 2 AM. Nobody is woken.",
        "fn": urgency_low_2am,
    },
    "urgency_high_2am": {
        "title": "02:00 — high urgency wakes deliberately",
        "description": "A leaking pipe at 2 AM. A neighbour is woken on purpose, and the log says so.",
        "fn": urgency_high_2am,
    },
    "availability_routing": {
        "title": "Availability routing",
        "description": "The obvious holder is out. NearMind routes around them.",
        "fn": availability_routing,
    },
    "busy_holder": {
        "title": "Busy holder",
        "description": "The only holder is busy. NearMind does not barge in.",
        "fn": busy_holder,
    },
    "handover_expiry_pivot": {
        "title": "Handover expiry → pivot",
        "description": "A neighbour says 'give me 5' then ghosts. NearMind checks back, then pivots.",
        "fn": handover_expiry_pivot,
    },
    "reciprocity": {
        "title": "Reciprocity nudge",
        "description": "Maryam owes Karim two favours; his reverse request is prioritised, with her consent.",
        "fn": reciprocity,
    },
}


def _pack(world: World, result) -> dict:
    return {
        "clock": world.clock.hhmm(),
        "request_id": result.request.id,
        "flow": result.to_dict(),
        "logs": [l.model_dump(mode="json") for l in world.logs],
        "threads": [
            {
                "neighbour_id": t.neighbour_id,
                "messages": [m.model_dump(mode="json") for m in t.messages],
            }
            for t in world.threads_for(result.request.id)
        ],
        "neighbours": [world.neighbour_view(nid) for nid in world.neighbours],
        "stats": dict(world.stats),
    }
