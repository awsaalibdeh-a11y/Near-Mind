"""Safety assessment and the veto.

The veto is the most important rule in the product: an unsafe ladder is never
recommended, even when nothing else exists. The veto lives here as
deterministic code on top of whatever the model says, because a model that
has been talked into "it's probably fine" must not be able to override a
structural hazard.

Defence in depth: the model may propose `safe`. The rules below may only ever
*tighten* a verdict, never loosen it.
"""

from __future__ import annotations

from typing import Any

from .models import SafetyStatus, SafetyVerdict

# Attributes that describe structural integrity. These are the ones where a
# wrong answer hurts someone.
_STRUCTURAL_ATTRS = ("stability", "missing_rung", "creaky", "wobbly", "broken", "cracked")

_UNSAFE_VALUES = ("creaky", "wobbly", "broken", "cracked", "loose", "unstable", "rusty", "unsafe", "yes")
_UNSAFE_WORDS = ("creaky", "wobbly", "broken", "cracked", "unstable", "collapsed", "splintered")

# Items where structural integrity is load-bearing (literally).
_CLIMB_ITEMS = ("ladder", "step ladder", "stool", "scaffold")


def is_climb_item(item: str) -> bool:
    return item.strip().lower() in _CLIMB_ITEMS


def structural_hazards(attributes: dict[str, str]) -> list[str]:
    """Any hazard we can read straight off the attributes, without the model."""
    hazards: list[str] = []
    for key, value in attributes.items():
        k = key.strip().lower()
        v = str(value).strip().lower()
        if k not in _STRUCTURAL_ATTRS:
            continue
        if v in _UNSAFE_VALUES or any(word in v for word in _UNSAFE_WORDS):
            if k == "missing_rung" and v == "no":
                continue
            hazards.append(f"{k}: {value}")
    return hazards


def tighten(item: str, condition: str, attributes: dict[str, str], verdict: SafetyVerdict) -> SafetyVerdict:
    """Apply deterministic rules on top of a model verdict. Only tightens.

    Order of severity: UNSAFE > NEEDS_CHECK > SAFE. `UNASSESSED` loses to
    anything that has an opinion.
    """
    hazards = structural_hazards(attributes)
    condition_l = (condition or "").strip().lower()
    if is_climb_item(item) and condition_l in _UNSAFE_WORDS:
        hazards.append(f"condition: {condition}")

    hazards = list(dict.fromkeys(hazards))

    if hazards:
        reason = verdict.reason.strip() or "Structural hazard reported."
        if verdict.status is not SafetyStatus.UNSAFE:
            reason = (
                f"{item} is not safe to lend: {', '.join(hazards)}. "
                "Falling from height is a serious injury risk, and NearMind will not "
                "put this item in front of Maryam even if it is the only one available."
            )
        return SafetyVerdict(
            status=SafetyStatus.UNSAFE,
            reason=reason,
            hazards=hazards,
            requires_condition=None,
        )

    if verdict.status in (SafetyStatus.SAFE, SafetyStatus.NEEDS_CHECK, SafetyStatus.UNSAFE):
        return verdict

    # Model gave us nothing usable. For a climb item, that means ask; for
    # anything else, an unassessed item is not a veto.
    if is_climb_item(item):
        return SafetyVerdict(
            status=SafetyStatus.NEEDS_CHECK,
            reason=(
                f"No condition information for this {item}. NearMind won't recommend "
                "it until the neighbour confirms it is sound."
            ),
            requires_condition="stability",
        )
    return SafetyVerdict(
        status=SafetyStatus.SAFE,
        reason=f"No safety-relevant attributes apply to {item}.",
    )


def is_usable(verdict: SafetyVerdict) -> bool:
    """Only safe items may be offered to Maryam."""
    return verdict.status is SafetyStatus.SAFE


def fake_assessment_payload(item: str, attributes: dict[str, str]) -> dict[str, Any]:
    """What the deterministic fake model 'thinks'. Real logic still applies."""
    hazards = structural_hazards(attributes)
    if hazards:
        return {
            "status": "unsafe",
            "reason": f"Reported condition is not sound: {', '.join(hazards)}.",
            "hazards": hazards,
        }
    if is_climb_item(item) and not attributes:
        return {
            "status": "needs_check",
            "reason": "No condition details were given.",
            "hazards": [],
            "requires_condition": "stability",
        }
    return {
        "status": "safe",
        "reason": f"Nothing in the reported condition of {item} suggests a hazard.",
        "hazards": [],
    }
