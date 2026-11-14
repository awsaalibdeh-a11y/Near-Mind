"""Who may be contacted, and why not.

This runs *before* any outreach. It produces a verdict per neighbour carrying
the reason, and those reasons go straight into the decision log. The product
promise is that the why is visible; this module is where the why is born.

Rules, in order:

1. **You must have it.** No item and no substitute → not eligible.
2. **Not at home → never contacted.** Their stock may still exist in the
   inventory; the person does not. NearMind does not pretend otherwise.
3. **Busy → route around.** Unless urgency is `emergency`, in which case a busy
   neighbour may be contacted but the log says why.
4. **Asleep → skip unless urgency justifies it.** `low` never wakes anyone;
   `high`/`emergency` may, and the wake is logged as an override.
5. **Fairness** only breaks ties between otherwise-equal candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .clock import human_window
from .models import Availability, InventoryItem, Neighbour, ParsedIntent, Urgency
from .world import World


@dataclass
class Eligibility:
    neighbour_id: str
    eligible: bool
    reason: str
    item: InventoryItem | None = None
    requested_as: str | None = None
    needs_wake: bool = False
    urgency_override: bool = False
    hazards: list[str] = field(default_factory=list)


def find_item(neighbour: Neighbour, intent: ParsedIntent) -> tuple[InventoryItem, str] | None:
    """Best-matching inventory item: exact first, then substitutes in order."""
    exact = [
        i for i in neighbour.inventory
        if i.item.strip().lower() == intent.item.strip().lower()
    ]
    if exact:
        return exact[0], intent.item
    for sub in intent.substitutes:
        for inv in neighbour.inventory:
            if inv.item.strip().lower() == sub.strip().lower():
                return inv, sub
    return None


def assess(neighbour: Neighbour, intent: ParsedIntent, world: World) -> Eligibility:
    local = world.local_time(neighbour)
    clock = local.strftime("%H:%M")
    state = world.availability_of(neighbour.id)
    sleep = human_window(neighbour.sleep_window)

    if state.state is Availability.NOT_AT_HOME:
        found = find_item(neighbour, intent)
        stock_note = (
            f" Their {found[0].item} may still be in the flat, but the person is not, "
            "so it is not theirs to lend."
            if found
            else ""
        )
        return Eligibility(
            neighbour_id=neighbour.id,
            eligible=False,
            reason=(
                f"{neighbour.label} is not at home ({state.reason}) since "
                f"{state.since:%H:%M}. NearMind does not contact people who are out."
                + stock_note
            ),
        )

    if state.state is Availability.BUSY:
        found = find_item(neighbour, intent)
        if intent.urgency is not Urgency.EMERGENCY:
            return Eligibility(
                neighbour_id=neighbour.id,
                eligible=False,
                reason=(
                    f"{neighbour.label} is at home but busy ({state.reason}) since "
                    f"{state.since:%H:%M}. Nobody answers a door mid-call for a "
                    f"{intent.item}; routing elsewhere."
                ),
            )
        if found is None:
            return Eligibility(
                neighbour_id=neighbour.id,
                eligible=False,
                reason=f"{neighbour.label} is busy and holds nothing that helps with {intent.item}.",
            )
        return Eligibility(
            neighbour_id=neighbour.id,
            eligible=True,
            reason=(
                f"{neighbour.label} is busy ({state.reason}) but urgency is emergency, "
                f"so NearMind interrupts rather than leaving Maryam stuck. Local time {clock}."
            ),
            item=found[0],
            requested_as=found[1],
            urgency_override=True,
        )

    asleep = world.is_asleep(neighbour)

    if asleep and intent.urgency is Urgency.LOW:
        return Eligibility(
            neighbour_id=neighbour.id,
            eligible=False,
            reason=(
                f"Skipped {neighbour.label}: local time {clock}, sleep window {sleep}. "
                f"{intent.item.capitalize()} is not urgent."
            ),
        )

    found = find_item(neighbour, intent)
    if found is None:
        subs = ", ".join(intent.substitutes) if intent.substitutes else "none offered"
        return Eligibility(
            neighbour_id=neighbour.id,
            eligible=False,
            reason=(
                f"{neighbour.label} has neither {intent.item} nor an acceptable "
                f"substitute ({subs})."
            ),
        )

    item, requested_as = found
    override = asleep
    return Eligibility(
        neighbour_id=neighbour.id,
        eligible=True,
        reason=(
            f"{neighbour.label} is available"
            + (" but asleep" if asleep else " and awake")
            + f" ({state.reason}) and has {item.item}."
            + (
                f" Waking them at {clock}: urgency is {intent.urgency.value}, "
                f"so this is a deliberate override of the sleep window {sleep}."
                if override
                else ""
            )
        ),
        item=item,
        requested_as=requested_as,
        needs_wake=asleep,
        urgency_override=override,
    )


def rank(candidates: list[Eligibility], world: World) -> list[Eligibility]:
    """Order eligible neighbours for outreach.

    Awake before asleep; then the neighbour owed the most (reciprocity reduces
    Maryam's debt), then fairness score. Deterministic tie-break on id.
    """
    from .ledger import owed_by_maryam

    def key(e: Eligibility):
        debt = owed_by_maryam(world, e.neighbour_id)
        fairness = world.neighbour(e.neighbour_id).fairness_score
        return (e.needs_wake, -debt, -fairness, e.neighbour_id)

    return sorted(candidates, key=key)
