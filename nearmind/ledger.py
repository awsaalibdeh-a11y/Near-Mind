"""The favour ledger and reciprocity routing.

The ledger is not a passive tally. When Maryam owes a neighbour, NearMind
*prioritises* that neighbour's reverse requests (things the neighbour asks
Maryam for) so she can pay the debt down. The nudge is suggested, never forced:
`reciprocity_suggestions` returns suggestions; nothing is routed until Maryam
confirms with `confirm_reciprocity`.
"""

from __future__ import annotations

from .models import LedgerDirection, LogAction, ReciprocitySuggestion
from .world import World


def owed_by_maryam(world: World, neighbour_id: str) -> int:
    return sum(
        1
        for e in world.ledger
        if not e.settled
        and e.direction is LedgerDirection.MARYAM_OWES
        and e.neighbour_id == neighbour_id
    )


def owed_to_maryam(world: World, neighbour_id: str) -> int:
    return sum(
        1
        for e in world.ledger
        if not e.settled
        and e.direction is LedgerDirection.NEIGHBOUR_OWES
        and e.neighbour_id == neighbour_id
    )


def balance(world: World) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for nid in world.neighbours:
        out[nid] = {
            "maryam_owes": owed_by_maryam(world, nid),
            "neighbour_owes": owed_to_maryam(world, nid),
            "net_maryam_owes": owed_by_maryam(world, nid) - owed_to_maryam(world, nid),
        }
    return out


def reciprocity_suggestions(world: World) -> list[ReciprocitySuggestion]:
    """Neighbours Maryam owes something to, most-indebted first.

    Only neighbours who are actually owed appear. A tie is broken by name so
    the suggestion list is stable across replays.
    """
    suggestions: list[ReciprocitySuggestion] = []
    for nid in world.neighbours:
        count = owed_by_maryam(world, nid)
        if count == 0:
            continue
        neighbour = world.neighbour(nid)
        items = [e.item for e in world.open_ledger(LedgerDirection.MARYAM_OWES) if e.neighbour_id == nid]
        suggestions.append(
            ReciprocitySuggestion(
                neighbour_id=nid,
                direction=LedgerDirection.MARYAM_OWES,
                open_count=count,
                summary=(
                    f"Maryam owes {neighbour.label} {count} favour"
                    f"{'s' if count != 1 else ''} ({', '.join(dict.fromkeys(items))})."
                ),
                reason=(
                    f"Maryam has borrowed from {neighbour.label} {count} time"
                    f"{'s' if count != 1 else ''} and not yet returned the favour. "
                    f"If {neighbour.name} asks Maryam for something, route it to her "
                    "first so she can pay it down."
                ),
            )
        )
    suggestions.sort(key=lambda s: (-s.open_count, world.neighbour(s.neighbour_id).name))
    return suggestions


def route_inbound(world: World, neighbour_id: str, item: str) -> tuple[bool, str, ReciprocitySuggestion | None]:
    """Decide whether an inbound (reverse) request goes to Maryam first.

    Returns `(route_to_maryam_first, reason, suggestion)`.
    """
    count = owed_by_maryam(world, neighbour_id)
    neighbour = world.neighbour(neighbour_id)
    if count <= 0:
        return (
            False,
            f"{neighbour.label} is not owed a favour, so there is no reciprocity reason to prioritise them.",
            None,
        )

    suggestion = ReciprocitySuggestion(
        neighbour_id=neighbour_id,
        direction=LedgerDirection.MARYAM_OWES,
        open_count=count,
        summary=f"{neighbour.label} asked Maryam for {item}.",
        reason=(
            f"{neighbour.label} has lent to Maryam {count} time"
            f"{'s' if count != 1 else ''} without repayment. Suggesting Maryam "
            f"takes this request on {item} to settle the debt — she confirms before "
            "NearMind tells the neighbour."
        ),
    )
    return True, suggestion.reason, suggestion


def confirm_reciprocity(
    world: World,
    suggestion: ReciprocitySuggestion,
    *,
    accepted: bool,
    item: str,
) -> str:
    """Maryam answers a reciprocity nudge. Never applied without her word."""
    neighbour = world.neighbour(suggestion.neighbour_id)
    if not accepted:
        world.log(
            action=LogAction.RECIPROCITY_SUGGESTED,
            reason=(
                f"Suggested {neighbour.label} to Maryam for reciprocity ({suggestion.open_count} owed); "
                "Maryam declined. The nudge is advisory and never forced, so the debt stays open."
            ),
            neighbours=[suggestion.neighbour_id],
            entities={"accepted": "false", "item": item},
        )
        return "declined"

    # Settle the oldest matching debt (or any open one for that neighbour).
    if not world.open_ledger(LedgerDirection.MARYAM_OWES):
        raise ValueError("there is no open debt to settle")
    open_entries = [
        e for e in world.open_ledger(LedgerDirection.MARYAM_OWES) if e.neighbour_id == suggestion.neighbour_id
    ]
    if open_entries:
        world.settle_ledger(open_entries[0].id)

    world.log(
        action=LogAction.RECIPROCITY_CONFIRMED,
        reason=(
            f"Maryam accepted {neighbour.label}'s request for {item}, settling one open "
            f"favour (owed: {suggestion.open_count} → {owed_by_maryam(world, suggestion.neighbour_id)}). "
            "Reciprocity routing prioritised them because Maryam owed them."
        ),
        neighbours=[suggestion.neighbour_id],
        entities={"accepted": "true", "item": item},
    )
    return "confirmed"
