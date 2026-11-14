"""Helpers for asserting *who was actually contacted*.

Tests and the UI both need this: 'nobody talked to the out-of-building
neighbour' is a property of threads, not of logs. Keeping it in one place
means the test cannot accidentally check the wrong thing.
"""

from __future__ import annotations

from .world import World


def contacted_ids(world: World, request_id: str) -> set[str]:
    """Neighbour ids with at least one near_mind message in this request."""
    ids: set[str] = set()
    for thread in world.threads_for(request_id):
        if any(m.role.value == "near_mind" for m in thread.messages):
            ids.add(thread.neighbour_id)
    return ids
