"""Handover state machine and the expiry sweep.

    proposed → agreed → collected → released

`released` is also reachable from any earlier stage (the neighbour released
NearMind, or Maryam pivoted). `expired` is a terminal state for an abandoned
handover, and the sweep then either checks back in or pivots to the
second-best offer.

The rule that matters: **Maryam is never left waiting**. Every open handover
has an expiry, and the sweep acts on it.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import (
    Handover,
    HandoverState,
    LogAction,
    Offer,
    OfferStatus,
    RequestStatus,
    ThreadRole,
)
from .world import World, new_id

_ALLOWED: dict[HandoverState, set[HandoverState]] = {
    HandoverState.PROPOSED: {HandoverState.AGREED, HandoverState.RELEASED, HandoverState.EXPIRED},
    HandoverState.AGREED: {HandoverState.COLLECTED, HandoverState.RELEASED, HandoverState.EXPIRED},
    HandoverState.COLLECTED: {HandoverState.RELEASED},
    HandoverState.RELEASED: set(),
    HandoverState.EXPIRED: set(),
}


class InvalidTransition(ValueError):
    pass


def open_handover(
    world: World,
    request_id: str,
    offer: Offer,
    *,
    minutes: int | None = None,
) -> Handover:
    now = world.now()
    minutes = minutes or world.settings.handover_expiry_minutes
    minutes = max(15, min(30, minutes))
    handover = Handover(
        id=new_id("ho"),
        request_id=request_id,
        offer_id=offer.id,
        neighbour_id=offer.neighbour_id,
        state=HandoverState.PROPOSED,
        created_at=now,
        expires_at=now.replace(microsecond=0) + timedelta(minutes=minutes),
    )
    handover.history = [(HandoverState.PROPOSED, now, "offer accepted by Maryam")]
    world.handovers[handover.id] = handover
    world.log(
        action=LogAction.HANDOVER_PROPOSED,
        reason=(
            f"Proposed handover with {world.neighbour(offer.neighbour_id).label} for "
            f"{offer.quantity:g}{offer.unit} {offer.item}. "
            f"Expires at {handover.expires_at:%H:%M} ({minutes} min) so Maryam is never "
            "left waiting if they go quiet."
        ),
        neighbours=[offer.neighbour_id],
        request_id=request_id,
        entities={"handover": handover.id, "offer": offer.id},
    )
    return handover


def _transition(world: World, handover: Handover, to: HandoverState, reason: str) -> Handover:
    if to not in _ALLOWED[handover.state]:
        raise InvalidTransition(f"{handover.state.value} → {to.value} is not allowed")
    now = world.now()
    handover.history.append((to, now, reason))
    handover.state = to
    return handover


def agree(world: World, handover: Handover, *, when: str = "") -> Handover:
    _transition(world, handover, HandoverState.AGREED, when or "neighbour confirmed")
    handover.agreed_at = world.now()
    world.log(
        action=LogAction.HANDOVER_AGREED,
        reason=(
            f"{world.neighbour(handover.neighbour_id).label} agreed to hand over. "
            f"{('They said: ' + when + '. ') if when else ''}"
            f"Pickup window closes at {handover.expires_at:%H:%M}."
        ),
        neighbours=[handover.neighbour_id],
        request_id=handover.request_id,
        entities={"handover": handover.id},
    )
    return handover


def collect(world: World, handover: Handover) -> Handover:
    _transition(world, handover, HandoverState.COLLECTED, "item collected")
    handover.collected_at = world.now()
    return handover


def release(world: World, handover: Handover, *, note: str = "") -> Handover:
    _transition(world, handover, HandoverState.RELEASED, note or "released")
    handover.released_at = world.now()
    return handover


# --------------------------------------------------------------------------- #
# Expiry sweep
# --------------------------------------------------------------------------- #


def sweep(world: World) -> list[dict]:
    """Act on every expired handover. Called by the tick, the API and tests.

    Behaviour: on first expiry we **check back** (a polite nudge to the
    neighbour) and give a short extra window. If that also expires, we
    **pivot** to the second-best offer, or close the request cleanly.
    Returns a list of outcome dicts for the API.
    """
    outcomes: list[dict] = []
    now = world.now()
    for handover in list(world.handovers.values()):
        if not handover.is_open or not handover.expired(now):
            continue
        outcomes.append(_expire(world, handover, now))
    return outcomes


def _expire(world: World, handover: Handover, now: datetime) -> dict:
    neighbour = world.neighbour(handover.neighbour_id)
    request = world.requests.get(handover.request_id)
    offer = world.offers.get(handover.offer_id)

    if handover.checked_back_at is None:
        handover.checked_back_at = now
        extra = max(15, world.settings.handover_expiry_minutes)
        handover.expires_at = now + timedelta(minutes=min(30, extra))
        thread = _thread_for(world, handover.request_id, handover.neighbour_id)
        if thread is not None:
            world.post(
                thread,
                ThreadRole.NEAR_MIND,
                "just checking — still ok for the handover? no rush, but i'll keep maryam posted",
            )
        world.log(
            action=LogAction.HANDOVER_EXPIRED,
            reason=(
                f"{neighbour.label} went quiet and the handover expired at "
                f"{now:%H:%M}. NearMind checked back in rather than leaving Maryam "
                f"waiting, and extended to {handover.expires_at:%H:%M}."
            ),
            neighbours=[neighbour.id],
            request_id=handover.request_id,
            entities={"handover": handover.id, "action": "checked_back"},
        )
        return {"handover": handover.id, "action": "checked_back", "neighbour": neighbour.id}

    # Second expiry: pivot.
    _transition(world, handover, HandoverState.EXPIRED, "expiry after check-back")
    if offer is not None and offer.status in (OfferStatus.ACCEPTED, OfferStatus.PROPOSED):
        offer.status = OfferStatus.RELEASED
    world.set_availability(
        neighbour.id,
        world.availability_of(neighbour.id).state,
        f"handover expired after check-back at {now:%H:%M}",
        set_by="system",
    )

    alternative = _next_offer(world, handover)
    if alternative is not None:
        world.log(
            action=LogAction.HANDOVER_PIVOTED,
            reason=(
                f"{neighbour.label} never came back after the check-back (expired "
                f"{now:%H:%M}). Pivoting to {world.neighbour(alternative.neighbour_id).label}'s "
                f"offer ({alternative.item}) rather than leaving Maryam waiting."
            ),
            neighbours=[neighbour.id, alternative.neighbour_id],
            request_id=handover.request_id,
            entities={"handover": handover.id, "pivot_offer": alternative.id},
        )
        alternative.status = OfferStatus.PROPOSED
        if request is not None:
            request.status = RequestStatus.AWAITING_CHOICE
        return {
            "handover": handover.id,
            "action": "pivoted",
            "to_offer": alternative.id,
            "to_neighbour": alternative.neighbour_id,
        }

    if request is not None:
        request.status = RequestStatus.NO_MATCH
        request.closure = (
            f"{neighbour.name} didn't come back in time, and nobody else has a usable "
            f"{request.intent.item}. Nothing lost — I'll keep an eye out."
        )
    world.log(
        action=LogAction.HANDOVER_PIVOTED,
        reason=(
            f"{neighbour.label} never came back (expired {now:%H:%M}) and there is no "
            "second offer to pivot to. Closing honestly instead of leaving Maryam waiting."
        ),
        neighbours=[neighbour.id],
        request_id=handover.request_id,
        entities={"handover": handover.id, "pivot_offer": "none"},
    )
    return {"handover": handover.id, "action": "closed", "neighbour": neighbour.id}


def _next_offer(world: World, handover: Handover) -> Offer | None:
    request_id = handover.request_id
    options = [
        o
        for o in world.offers.values()
        if o.request_id == request_id
        and o.neighbour_id != handover.neighbour_id
        and o.status is OfferStatus.PROPOSED
    ]
    options.sort(key=lambda o: (-o.score, o.neighbour_id))
    return options[0] if options else None


def _thread_for(world: World, request_id: str, neighbour_id: str):
    for t in world.threads_for(request_id):
        if t.neighbour_id == neighbour_id:
            return t
    return None
