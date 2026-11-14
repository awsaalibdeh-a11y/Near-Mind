"""Strict schemas for every model call, and graceful degradation.

Rules:

* Every call declares the model it expects (`ParsedIntent`, `ReplyReading`,
  `SafetyAssessment`, `LedgerUpdate`).
* A reply that cannot be validated is **never** applied to state. It is
  reported as `SchemaOutcome` with `ok=False`, and the caller decides a
  conservative fallback (usually "ask the neighbour to repeat themselves").
* We attempt one narrow, well-defined repair: strip markdown fences, pull the
  first JSON object, coerce obvious scalar types. We never invent missing
  semantic content — inventing a quantity is how a ledger gets corrupted.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, Field, ValidationError

from .models import SafetyStatus, Urgency

T = TypeVar("T", bound="BaseModel")

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


@dataclass
class SchemaOutcome:
    ok: bool
    model: BaseModel | None = None
    error: str | None = None
    repaired: bool = False
    raw: str = ""

    def require(self) -> BaseModel:
        if not self.ok or self.model is None:
            raise ValueError(f"schema outcome is not ok: {self.error}")
        return self.model


# --------------------------------------------------------------------------- #
# Model-output schemas
# --------------------------------------------------------------------------- #


class IntentSchema(BaseModel):
    """Strict schema for 'what did Maryam ask for'."""

    item: str = Field(min_length=1)
    quantity: float = Field(default=1.0, gt=0, le=1000)
    unit: str = "pcs"
    urgency: Urgency = Urgency.LOW
    substitutes: list[str] = Field(default_factory=list)
    safety_attributes: list[str] = Field(default_factory=list)
    purpose: str = ""
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class ReplySchema(BaseModel):
    """Strict schema for reading a neighbour's free-text reply.

    Real neighbours write anything. The model's job is to map it onto this
    shape; if it cannot, the caller falls back to 'unclear' and asks.
    """

    has_item: bool | None = None
    item: str | None = None
    quantity: float | None = Field(default=None, ge=0, le=1000)
    unit: str | None = None
    condition: str | None = None
    vague: bool = False
    question: str | None = None
    wait_minutes: int | None = Field(default=None, ge=0, le=1440)
    decline: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class SafetySchema(BaseModel):
    status: SafetyStatus = SafetyStatus.UNASSESSED
    reason: str = ""
    hazards: list[str] = Field(default_factory=list)
    requires_condition: str | None = None


class LedgerSchema(BaseModel):
    """Only applied after a handover completes. Never mid-conversation."""

    direction: str = "maryam_owes"
    item: str
    note: str = ""


class ClarificationSchema(BaseModel):
    question: str = Field(min_length=1)
    about: str = ""


class StyleSchema(BaseModel):
    text: str = Field(min_length=1)


# --------------------------------------------------------------------------- #
# Repair helpers
# --------------------------------------------------------------------------- #


def _strip_fence(raw: str) -> str:
    m = _FENCE.search(raw)
    if m:
        return m.group(1)
    return raw


def _first_json_object(raw: str) -> str | None:
    start = raw.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    return None


def _coerce_loose(obj: dict[str, Any]) -> dict[str, Any]:
    """Coerce only scalar types that are unambiguous. No semantic invention."""
    out = dict(obj)
    for key in ("quantity", "confidence", "wait_minutes"):
        if key in out and isinstance(out[key], str) and out[key].strip():
            try:
                out[key] = float(out[key].strip().rstrip("%"))
            except ValueError:
                pass
    if "condition" in out and out["condition"] is None:
        out.pop("condition")
    return out


def validate_payload(schema: type[T], payload: str | dict[str, Any] | None) -> SchemaOutcome:
    """Validate a model reply against a strict schema.

    Returns a `SchemaOutcome`; never raises for malformed input.
    """
    if payload is None:
        return SchemaOutcome(ok=False, error="empty model output", raw="")
    if isinstance(payload, dict):
        raw = json.dumps(payload)
        obj = payload
        candidate = payload
    else:
        raw = str(payload)
        text = _strip_fence(raw)
        extracted = _first_json_object(text)
        if extracted is None:
            return SchemaOutcome(
                ok=False,
                error="no JSON object in model output",
                raw=raw,
            )
        try:
            candidate = json.loads(extracted)
        except json.JSONDecodeError as exc:
            return SchemaOutcome(ok=False, error=f"invalid JSON: {exc}", raw=raw)
        obj = candidate

    if not isinstance(candidate, dict):
        return SchemaOutcome(ok=False, error="model output is not a JSON object", raw=raw)

    try:
        model = schema.model_validate(obj)
        return SchemaOutcome(ok=True, model=model, raw=raw)
    except ValidationError as exc:
        first_error = str(exc)

    repaired = _coerce_loose(obj)
    if repaired != obj:
        try:
            model = schema.model_validate(repaired)
            return SchemaOutcome(ok=True, model=model, repaired=True, raw=raw)
        except ValidationError as exc:
            first_error = str(exc)

    return SchemaOutcome(ok=False, error=first_error, repaired=False, raw=raw)


def json_schema_for(schema: type[BaseModel]) -> dict[str, Any]:
    return schema.model_json_schema()
