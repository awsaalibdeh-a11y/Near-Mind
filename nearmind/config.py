"""Configuration and the sandbox seed.

The third neighbour's name is deliberately not hard-coded in logic: it is
read from `NEARMIND_THIRD_NAME` (default `Umm Samir`) so the cast can change
without touching a single rule.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Settings:
    model_name: str = os.getenv("NEARMIND_MODEL", "gpt-5-mini")
    use_fake_model: bool = os.getenv("NEARMIND_FAKE_MODEL", "1") != "0"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    third_neighbour_name: str = os.getenv("NEARMIND_THIRD_NAME", "Umm Samir")
    enable_whatsapp_bridge: bool = os.getenv("NEARMIND_WHATSAPP", "0") == "1"
    handover_expiry_minutes: int = int(os.getenv("NEARMIND_HANDOVER_MINUTES", "20"))
    state_path: str = os.getenv("NEARMIND_STATE", "")
    # Virtual clock start. Overridable so tests and demos are reproducible.
    start_time: datetime = field(
        default_factory=lambda: os.getenv("NEARMIND_START")
        and datetime.fromisoformat(os.environ["NEARMIND_START"])  # type: ignore[arg-type]
        or datetime(2026, 11, 14, 19, 0, 0)
    )
    auto_expire: bool = os.getenv("NEARMIND_AUTO_EXPIRE", "1") != "0"


def settings_from_env() -> Settings:
    return Settings()


# --------------------------------------------------------------------------- #
# Sandbox seed: three AI neighbours with hidden stock
# --------------------------------------------------------------------------- #

NEIGHBOUR_SEED: list[dict] = [
    {
        "id": "karim",
        "house_number": "12",
        "name": "Karim",
        "personality": (
            "Eager, slightly chaotic, always mid-project. Helps first, thinks later. "
            "Proud of his toolbox and will mention it."
        ),
        "texting_style": (
            "Short bursts, lower-case, no full stops, occasional 'walaw'. Sends two "
            "messages where one would do."
        ),
        "sleep_window": ("23:00", "06:30"),
        "clock_offset_minutes": 0,
        "fairness_score": 0.5,
        "inventory": [
            {"item": "salt", "quantity": 1, "unit": "kg", "condition": "good"},
            {"item": "ladder", "quantity": 1, "condition": "creaky", "tags": ["tool"],
             "attributes": {"stability": "creaky", "missing_rung": "no", "last_used": "3 years ago"}},
            {"item": "baking soda", "quantity": 200, "unit": "g", "condition": "good"},
            {"item": "drill", "quantity": 1, "condition": "good", "tags": ["tool"]},
        ],
    },
    {
        "id": "ali",
        "house_number": "8",
        "name": "Ali",
        "personality": (
            "Precise, measured, a little formal. Answers with exactly the information "
            "asked for and expects the same. Keeps an inventory list on his phone."
        ),
        "texting_style": (
            "Full sentences, capitals, correct punctuation. Rarely uses 'I' — says "
            "'we have' because it is his household."
        ),
        "sleep_window": ("22:00", "07:00"),
        "clock_offset_minutes": 0,
        "fairness_score": 0.5,
        "inventory": [
            {"item": "white vinegar", "quantity": 500, "unit": "ml", "condition": "good"},
            {"item": "lemon juice", "quantity": 250, "unit": "ml", "condition": "good"},
            {"item": "step ladder", "quantity": 1, "condition": "good", "tags": ["tool"],
             "attributes": {"stability": "stable", "max_load_kg": "150"}},
            {"item": "first aid kit", "quantity": 1, "condition": "good"},
        ],
    },
]

THIRD_NEIGHBOUR_SEED: dict = {
    "id": "umm_samir",
    "house_number": "14",
    "name": "Umm Samir",
    "personality": (
        "Warm, unhurried, looks after the building. Has everything, forgets where "
        "she put it. Will invite you in for tea and forget the original request."
    ),
    "texting_style": (
        "Voice-note energy in text: long, affectionate, ellipses, 'habibti', "
        "sometimes answers a question you didn't ask."
    ),
    "sleep_window": ("21:30", "05:30"),
    "clock_offset_minutes": 0,
    "fairness_score": 0.5,
    "inventory": [
        {"item": "baking soda", "quantity": 50, "unit": "g", "condition": "good"},
        {"item": "flour", "quantity": 1, "unit": "kg", "condition": "good"},
        {"item": "ladder", "quantity": 1, "condition": "old", "tags": ["tool"],
         "attributes": {"stability": "wobbly", "missing_rung": "yes", "age": "20 years"}},
        {"item": "paracetamol", "quantity": 1, "unit": "pack", "condition": "good",
         "tags": ["medical"]},
    ],
}


def seed_neighbours(third_name: str) -> list[dict]:
    """Return the cast with the configurable third name applied."""
    third = dict(THIRD_NEIGHBOUR_SEED)
    third["name"] = third_name
    return [*NEIGHBOUR_SEED, third]
