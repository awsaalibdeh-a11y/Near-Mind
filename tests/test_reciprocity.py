"""Reciprocity routing in the favour ledger.

The nudge is suggested, never forced. Two debts owed to Karim must make his
reverse request reach Maryam first — but only after she says yes.
"""

from datetime import datetime

from nearmind.config import Settings
from nearmind.ledger import (
    balance,
    confirm_reciprocity,
    owed_by_maryam,
    reciprocity_suggestions,
    route_inbound,
)
from nearmind.models import LedgerDirection
from nearmind.world import World

T0 = datetime(2026, 11, 14, 19, 0)


def _world() -> World:
    w = World.sandbox(Settings(start_time=T0))
    w.reply_script = {}
    return w


def _owe(w: World, neighbour_id: str, item: str) -> None:
    w.add_ledger(LedgerDirection.MARYAM_OWES, neighbour_id, item)


def test_two_debts_rank_first():
    w = _world()
    _owe(w, "karim", "drill")
    _owe(w, "karim", "baking soda")
    _owe(w, "ali", "flour")

    suggestions = reciprocity_suggestions(w)
    assert suggestions[0].neighbour_id == "karim"
    assert suggestions[0].open_count == 2
    assert "2 favours" in suggestions[0].summary


def test_reverse_request_routes_to_maryam_first():
    w = _world()
    _owe(w, "karim", "drill")
    _owe(w, "karim", "baking soda")

    route, reason, suggestion = route_inbound(w, "karim", "sugar")
    assert route is True
    assert suggestion is not None
    assert "2 times" in reason


def test_no_debt_no_priority():
    w = _world()
    route, reason, suggestion = route_inbound(w, "ali", "sugar")
    assert route is False
    assert suggestion is None


def test_nudge_is_never_forced():
    w = _world()
    _owe(w, "karim", "drill")
    suggestion = reciprocity_suggestions(w)[0]

    confirm_reciprocity(w, suggestion, accepted=False, item="sugar")
    # Debt unchanged: declining the nudge must not settle anything.
    assert owed_by_maryam(w, "karim") == 1


def test_confirming_settles_exactly_one_favour():
    w = _world()
    _owe(w, "karim", "drill")
    _owe(w, "karim", "baking soda")
    suggestion = reciprocity_suggestions(w)[0]

    confirm_reciprocity(w, suggestion, accepted=True, item="sugar")
    assert owed_by_maryam(w, "karim") == 1
    confirmed = [l for l in w.logs if l.action.value == "reciprocity_confirmed"]
    assert confirmed
    assert "settling one open favour" in confirmed[0].reason


def test_balance_is_two_way():
    w = _world()
    _owe(w, "karim", "drill")
    w.add_ledger(LedgerDirection.NEIGHBOUR_OWES, "ali", "flour")
    b = balance(w)
    assert b["karim"]["net_maryam_owes"] == 1
    assert b["ali"]["net_maryam_owes"] == -1


def test_reciprocity_cannot_settle_a_debt_that_does_not_exist():
    """Regression: confirming with no open debt must fail, not fake a settlement."""
    import pytest

    w = _world()
    suggestion = reciprocity_suggestions(w)
    assert suggestion == []
    from nearmind.models import ReciprocitySuggestion

    fake = ReciprocitySuggestion(
        neighbour_id="karim",
        direction=LedgerDirection.MARYAM_OWES,
        open_count=1,
        summary="none",
        reason="none",
    )
    with pytest.raises(ValueError):
        confirm_reciprocity(w, fake, accepted=True, item="sugar")
