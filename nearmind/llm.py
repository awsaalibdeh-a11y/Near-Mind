"""The model layer.

Three implementations behind one protocol:

* `FakeModel` — deterministic, rule-based, no network. The showcase and the
  tests run on this exclusively.
* `OpenAIModel` — `gpt-5-mini` via the OpenAI SDK; strict JSON schema mode.
* `FailingModel` — deliberately broken, used by tests to prove schema failure
  degrades gracefully.

Methods return **raw text**. Validation happens in the caller via
`schemas.validate_payload`, so a bad reply can never reach state by accident.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Protocol

from .models import Neighbour, ParsedIntent, Urgency
from .schemas import ReplySchema, validate_payload


class ModelProtocol(Protocol):
    """The five things NearMind asks the model to do."""

    def parse_intent(self, message: str) -> str: ...
    def read_reply(self, reply: str, item: str) -> str: ...
    def assess_safety(self, item: str, attributes: dict[str, str]) -> str: ...
    def compose_outreach(self, neighbour: Neighbour, intent: ParsedIntent, clock: str) -> str: ...
    def compose_clarification(self, neighbour: Neighbour, item: str, missing: str) -> str: ...


# --------------------------------------------------------------------------- #
# Deterministic fake model
# --------------------------------------------------------------------------- #

_ITEM_SYNONYMS: dict[str, str] = {
    "bicarb": "baking soda",
    "bicarbonate": "baking soda",
    "sodium bicarbonate": "baking soda",
    "sel": "salt",
    "tree": "ladder",
    "step stool": "ladder",
    "stepladder": "step ladder",
    "vinegar": "white vinegar",
    "painkiller": "paracetamol",
    "panadol": "paracetamol",
    "tylenol": "paracetamol",
}

# Substitutes NearMind will accept when it can reason about them.
_SUBSTITUTES: dict[str, list[str]] = {
    "salt": [],
    "baking soda": ["white vinegar", "lemon juice"],
    "ladder": ["step ladder"],
    "sugar": ["baking soda"],
    "first aid kit": ["paracetamol"],
}

_SAFETY_ATTRS: dict[str, list[str]] = {
    "ladder": ["stability", "missing_rung", "max_load_kg", "creaky", "wobbly"],
}

_EMERGENCY_WORDS = re.compile(
    r"\b(emergency|flooding|flood|leak(?:ing)?|burst pipe|chest pain|can'?t breathe|"
    r"bleeding|fainted|fire|smoke|urgent(?:ly)?)\b",
    re.IGNORECASE,
)
_HIGH_WORDS = re.compile(
    r"\b(now|right away|asap|tonight|quick(?:ly)?|need it (?:now|today)|soon)\b",
    re.IGNORECASE,
)
_QTY = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|ml|l|litre|liter|pack|packs|piece|pieces|pcs)?")

_DECLINE = re.compile(
    r"\b(no|nope|nah|don'?t have|don't got|gave (?:it )?(?:away|out)|out of|finished|ran out|"
    r"already (?:lent|borrowed))\b",
    re.IGNORECASE,
)
_AFFIRM = re.compile(r"\b(yes|yeah|yep|sure|have|got|i've got|we have|of course|hawe)\b", re.IGNORECASE)
_WAIT = re.compile(
    r"\b(give me|gimme|wait|hold on|one sec|a sec|a minute|min|moment|second)\b\s*(\d+)?",
    re.IGNORECASE,
)
_VAGUE = re.compile(
    r"\b(pink stuff|that stuff|the usual|you know|the white one|the stuff|some kind)\b",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"(how much|what for|which one|do you need|when do you|how many|for what|what size)",
    re.IGNORECASE,
)
_ITEM_IN_REPLY = re.compile(
    r"\b(baking soda|bicarb|salt|vinegar|lemon juice|flour|ladder|step ladder|paracetamol|"
    r"first aid kit|drill|sugar)\b",
    re.IGNORECASE,
)


def _normalise(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip().lower()


class FakeModel:
    """Rule-based stand-in for `gpt-5-mini`.

    Deterministic on purpose: same input, same output, every time. This is what
    makes the showcase replayable and the tests meaningful.
    """

    def parse_intent(self, message: str) -> str:
        text = _normalise(message)
        item = self._find_item(text)
        if item is None:
            # Unknown item: do not invent a schema-valid answer. Returning a
            # sentinel would be a *false* parse and would put a fake noun in
            # front of Maryam. The caller downgrades instead.
            return json.dumps({"__unparsed__": True, "raw": message})
        quantity, unit = 1.0, "pcs"
        m = _QTY.search(text)
        if m:
            quantity = float(m.group(1))
            unit = self._unit(m.group(2), item)

        urgency = Urgency.LOW
        if _EMERGENCY_WORDS.search(text):
            urgency = Urgency.EMERGENCY
        elif _HIGH_WORDS.search(text):
            urgency = Urgency.HIGH

        substitutes = _SUBSTITUTES.get(item, [])
        safety_attributes = _SAFETY_ATTRS.get(item, [])
        purpose = ""
        if "smoke detector" in text or "smoke alarm" in text:
            purpose = "reaching the smoke detector"
        elif "dinner" in text or "recipe" in text or "cook" in text:
            purpose = "cooking"

        return json.dumps(
            {
                "item": item,
                "quantity": quantity,
                "unit": unit,
                "urgency": urgency.value,
                "substitutes": substitutes,
                "safety_attributes": safety_attributes,
                "purpose": purpose,
                "confidence": 0.9,
            }
        )

    def _find_item(self, text: str) -> str | None:
        for synonym, canonical in _ITEM_SYNONYMS.items():
            if synonym in text:
                return canonical
        # Prefer the longest known item so "step ladder" beats "ladder".
        from .config import seed_neighbours

        known: set[str] = set()
        for entry in seed_neighbours("whatever"):
            for inv in entry["inventory"]:
                known.add(inv["item"].lower())
        for known_item in sorted(known, key=len, reverse=True):
            if known_item in text:
                return known_item
        return None

    def _unit(self, raw: str | None, item: str) -> str:
        if not raw:
            if item in {"ladder", "step ladder", "drill", "first aid kit"}:
                return "pcs"
            if item in {"salt", "flour"}:
                return "kg"
            return "pcs"
        mapping = {"litre": "l", "liter": "l", "piece": "pcs", "pieces": "pcs", "packs": "pack"}
        return mapping.get(raw, raw)

    def read_reply(self, reply: str, item: str) -> str:
        text = _normalise(reply)
        payload: dict = {}

        if _WAIT.search(text) and not _DECLINE.search(text):
            m = re.search(r"(\d+)\s*(?:min|minute|sec|second|moment)", text)
            wait = int(m.group(1)) if m else 5
            if re.search(r"sec|second", text) and not re.search(r"min|minute", text):
                wait = 1
            payload.update(
                {
                    "has_item": True,
                    "item": item,
                    "wait_minutes": wait,
                    "vague": False,
                    "confidence": 0.8,
                }
            )
            return ReplySchema(**payload).model_dump_json()

        if _DECLINE.search(text):
            payload.update({"has_item": False, "decline": True, "confidence": 0.85})
            return json.dumps(payload)

        question = None
        if _QUESTION.search(text):
            question = reply.strip()

        vague = bool(_VAGUE.search(text))
        found = _ITEM_IN_REPLY.search(text)
        mentioned = found.group(1).lower() if found else None

        condition = None
        for word in ("creaky", "wobbly", "old", "broken", "rusty", "new", "sturdy"):
            if word in text:
                condition = word

        has_item: bool | None = None
        if _AFFIRM.search(text):
            has_item = True
        elif mentioned:
            has_item = True

        payload = {
            "has_item": has_item,
            "item": mentioned or (None if vague else item),
            "vague": vague,
            "question": question,
            "condition": condition,
            "confidence": 0.55 if vague else 0.85,
        }
        if vague and not mentioned:
            payload["item"] = None
        if mentioned and mentioned != item:
            payload["item"] = mentioned
        return json.dumps(payload)

    def assess_safety(self, item: str, attributes: dict[str, str]) -> str:
        from .safety import fake_assessment_payload

        return json.dumps(fake_assessment_payload(item, attributes))

    def compose_outreach(self, neighbour: Neighbour, intent: ParsedIntent, clock: str) -> str:
        """Compose a message in the neighbour's style.

        The *content* is fixed by the flow (item, quantity, urgency). Only the
        register changes — which is exactly what 'each in their own style'
        should mean. Returned as JSON text, like a real model would.
        """
        qty = _format_qty(intent.quantity, intent.unit)
        noun = _article_phrase(intent.item, qty)
        urgency_note = {
            Urgency.LOW: "",
            Urgency.HIGH: " sorry it's a bit of a rush",
            Urgency.EMERGENCY: " sorry to bother you properly",
        }[intent.urgency]

        if neighbour.id == "karim":
            text = (
                f"karim! maryam from #10 here. she's after {noun}{urgency_note}. "
                f"have you got any?? she's not asking you to go door to door, just you first. walaw"
            )
        elif neighbour.id == "ali":
            text = (
                f"Good evening. Maryam from #10 is asking whether we have {noun} "
                f"available to borrow{urgency_note}. A yes or no is sufficient."
            )
        elif neighbour.id == "umm_samir":
            text = (
                f"habibti, it's Maryam from number 10... she's asking if you happen to have "
                f"{noun}... no pressure at all, whenever you get a moment{urgency_note}"
            )
        else:
            text = (
                f"Hi {neighbour.name.split()[0]}, Maryam from #10 is asking whether you have "
                f"{noun} to lend{urgency_note}."
            )
        return json.dumps({"text": text})

    def compose_clarification(self, neighbour: Neighbour, item: str, missing: str) -> str:
        if neighbour.id == "karim":
            text = f"ah ok — {missing}? just so i don't send her the wrong one"
        elif neighbour.id == "ali":
            text = f"Understood. Could you confirm {missing}? Thank you."
        elif neighbour.id == "umm_samir":
            text = f"habibti just so i understand... {missing}? forgive me, my head... "
        else:
            text = f"Sorry, could you confirm {missing}?"
        return json.dumps({"text": text})


_COUNTABLE = {"ladder", "step ladder", "drill", "first aid kit", "whisk", "pot", "pan", "tool"}


def _article_phrase(item: str, qty: str) -> str:
    """'a ladder', '2kg of salt', 'some salt' — read like a person wrote it."""
    if qty == "one":
        return f"a {item}" if item in _COUNTABLE else f"some {item}"
    # Unit-less counts are piece counts; mass/volume units read better with 'of'.
    if qty.replace(".", "").replace("-", "").isdigit():
        return f"{qty} {item if item.endswith('s') else item}"
    if any(u in qty for u in ("kg", "g", "ml", "l")):
        return f"{qty} of {item}"
    return f"some {item}"


def _format_qty(quantity: float, unit: str) -> str:
    q = int(quantity) if float(quantity).is_integer() else quantity
    if unit == "pcs":
        return f"{q}" if q != 1 else "one"
    return f"{q}{unit}" if unit in {"kg", "g", "ml", "l"} else f"{q} {unit}"


# --------------------------------------------------------------------------- #
# Failing model (for degradation tests)
# --------------------------------------------------------------------------- #


class FailingModel(FakeModel):
    """Every call returns something that is *not* the declared schema.

    Used to prove that a model going off-script cannot corrupt state.
    """

    def __init__(self, mode: str = "prose") -> None:
        self.mode = mode

    def _bad(self) -> str:
        if self.mode == "prose":
            return "yeah I think so?? lol"
        if self.mode == "empty":
            return ""
        if self.mode == "wrong-hidden":
            return json.dumps({"quantity": -5, "confidence": "very high"})
        if self.mode == "json-array":
            return json.dumps([1, 2, 3])
        return "not json at all"

    def parse_intent(self, message: str) -> str:  # type: ignore[override]
        return self._bad()

    def read_reply(self, reply: str, item: str) -> str:  # type: ignore[override]
        return self._bad()

    def assess_safety(self, item: str, attributes: dict[str, str]) -> str:  # type: ignore[override]
        return self._bad()

    def compose_outreach(self, neighbour: Neighbour, intent: ParsedIntent, clock: str) -> str:  # type: ignore[override]
        return self._bad()

    def compose_clarification(self, neighbour: Neighbour, item: str, missing: str) -> str:  # type: ignore[override]
        return self._bad()


# --------------------------------------------------------------------------- #
# OpenAI implementation
# --------------------------------------------------------------------------- #


class OpenAIModel:
    """`gpt-5-mini` with strict JSON schema response format."""

    def __init__(self, api_key: str, model: str = "gpt-5-mini") -> None:
        from openai import OpenAI  # imported lazily: fake mode must not need it

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def _json(self, system: str, user: str, schema_name: str, schema: dict) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        )
        return resp.choices[0].message.content or ""

    def parse_intent(self, message: str) -> str:
        from .schemas import IntentSchema, json_schema_for

        return self._json(
            "You extract neighbourly favours into a strict schema. Never invent a "
            "quantity you were not told; default to 1. Urgency is 'emergency' only "
            "for danger to health, safety or property; 'high' for time pressure; "
            "otherwise 'low'.",
            message,
            "intent",
            json_schema_for(IntentSchema),
        )

    def read_reply(self, reply: str, item: str) -> str:
        from .schemas import ReplySchema, json_schema_for

        return self._json(
            f"A neighbour replied about '{item}'. Map their words onto the schema. "
            "Keep uncertainty in `vague` and `confidence`; do not guess a quantity.",
            reply,
            "reply",
            json_schema_for(ReplySchema),
        )

    def assess_safety(self, item: str, attributes: dict[str, str]) -> str:
        from .schemas import SafetySchema, json_schema_for

        return self._json(
            "Assess whether a borrowed item is safe to use. Veto anything whose "
            "structural integrity is doubtful. Name concrete hazards. A missing "
            "attribute is a reason to ask, not to assume safe.",
            json.dumps({"item": item, "attributes": attributes}),
            "safety",
            json_schema_for(SafetySchema),
        )

    def compose_outreach(self, neighbour: Neighbour, intent: ParsedIntent, clock: str) -> str:
        from .schemas import StyleSchema, json_schema_for

        return self._json(
            "Write a short message from NearMind to a neighbour, in their style. "
            f"Style: {neighbour.texting_style}. Personality: {neighbour.personality}. "
            "Ask only for what is needed. Do not invent offers.",
            json.dumps(
                {
                    "neighbour": neighbour.name,
                    "item": intent.item,
                    "quantity": intent.quantity,
                    "unit": intent.unit,
                    "urgency": intent.urgency.value,
                    "clock": clock,
                }
            ),
            "message",
            json_schema_for(StyleSchema),
        )

    def compose_clarification(self, neighbour: Neighbour, item: str, missing: str) -> str:
        from .schemas import StyleSchema, json_schema_for

        return self._json(
            f"Ask one short clarifying question in this neighbour's style: {neighbour.texting_style}.",
            json.dumps({"item": item, "missing": missing}),
            "message",
            json_schema_for(StyleSchema),
        )


class ValidatingModel:
    """Wraps any model so every call is validated, with honest downgrades.

    The flow must never see an unvalidated payload. `ValidatingModel` returns
    `(outcome, raw)` and records schema failures on the world.
    """

    def __init__(self, inner) -> None:
        self.inner = inner

    # -- helpers ------------------------------------------------------------

    def parse_intent(self, message: str):
        from .schemas import IntentSchema

        raw = _safe_call(self.inner.parse_intent, message)
        return validate_payload(IntentSchema, raw), raw

    def read_reply(self, reply: str, item: str):
        from .schemas import ReplySchema, validate_payload

        raw = _safe_call(self.inner.read_reply, reply, item)
        return validate_payload(ReplySchema, raw), raw

    def assess_safety(self, item: str, attributes: dict[str, str]):
        from .schemas import SafetySchema

        raw = _safe_call(self.inner.assess_safety, item, attributes)
        return validate_payload(SafetySchema, raw), raw

    def compose_outreach(self, neighbour, intent, clock: str):
        from .schemas import StyleSchema

        raw = _safe_call(self.inner.compose_outreach, neighbour, intent, clock)
        return validate_payload(StyleSchema, raw), raw

    def compose_clarification(self, neighbour, item: str, missing: str):
        from .schemas import StyleSchema

        raw = _safe_call(self.inner.compose_clarification, neighbour, item, missing)
        return validate_payload(StyleSchema, raw), raw


def _safe_call(fn, *args) -> str | None:
    try:
        out = fn(*args)
    except Exception as exc:  # network, auth, rate limit — degrade, don't crash
        return json.dumps({"__error__": str(exc)})
    return out if isinstance(out, str) else json.dumps(out)
