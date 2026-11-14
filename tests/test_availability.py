"""Availability gating: who gets contacted, and who must never be.

The promise is not merely 'availability is stored'. It is: an out-of-building
neighbour is *never* contacted, a busy one is routed around unless it is an
emergency, and a sleeping one is left alone unless urgency says otherwise.
"""

from nearmind.availability_probe import contacted_ids
from nearmind.agent import Agent
from nearmind.llm import FakeModel
from nearmind.models import Availability


def _run(world, message):
    return Agent(world, FakeModel()).handle(message)


def test_not_at_home_is_never_contacted(world):
    world.set_availability("karim", Availability.NOT_AT_HOME, "Out at the gym", set_by="sandbox")
    world.reply_script = {("ali", "baking soda"): "We have white vinegar and lemon juice."}

    result = _run(world, "anyone have baking soda?")

    assert "karim" not in contacted_ids(world, result.request.id)
    assert "karim" not in [t.neighbour_id for t in world.threads_for(result.request.id)]
    # The reason must be in the log, not just an absence.
    assert any(
        log.action.value == "skipped_neighbour"
        and log.neighbours == ["karim"]
        and "not at home" in log.reason
        for log in world.logs
    )


def test_not_at_home_stock_exists_but_person_does_not(world):
    """Karim has salt; he is out. Knowing he has it must not turn into contact."""
    world.set_availability("karim", Availability.NOT_AT_HOME, "Away for the weekend")
    result = _run(world, "anyone have salt?")
    assert not result.offers
    assert "karim" not in contacted_ids(world, result.request.id)


def test_busy_is_routed_around_for_low_urgency(world):
    world.set_availability("karim", Availability.BUSY, "On a work call", minutes=30)
    world.reply_script = {("ali", "baking soda"): "We have white vinegar."}
    result = _run(world, "anyone have baking soda?")
    assert "karim" not in contacted_ids(world, result.request.id)
    assert result.offers, "NearMind should have found Ali's substitute instead"
    assert all(o.neighbour_id != "karim" for o in result.offers)


def test_busy_needs_a_self_expiring_window(world):
    world.set_availability("karim", Availability.BUSY, "Cooking", minutes=20)
    state = world.availability_of("karim")
    assert state.expires_at is not None
    world.tick(25)
    assert world.availability_of("karim").state is Availability.AVAILABLE


def test_stop_holds_until_changed(world):
    world.set_availability("karim", Availability.NOT_AT_HOME, "STOP requested via WhatsApp", set_by="whatsapp")
    world.tick(24 * 60)  # a day later, no window, so it still holds
    assert world.availability_of("karim").state is Availability.NOT_AT_HOME


def test_asleep_is_skipped_for_low_urgency(world):
    world.clock.set(world.now().replace(hour=2, minute=0))
    result = _run(world, "anyone have salt? for dinner")
    assert "karim" not in contacted_ids(world, result.request.id)
    assert result.request.status.value == "no_match"
    assert any("sleep window" in log.reason for log in world.logs)


def test_home_but_asleep_is_a_distinct_state(world):
    """available + asleep, not an availability enum value of its own."""
    world.clock.set(world.now().replace(hour=2, minute=0))
    view = world.neighbour_view("ali")
    assert view["availability"]["state"] == "available"
    assert view["asleep"] is True
