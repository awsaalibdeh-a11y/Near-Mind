"""Domain models for NearMind.

Every object that can leave the backend is a pydantic model with an explicit
schema. Nothing here talks to the network or the clock — the world owns time.

The reason-carrying models (`DecisionLog`, `ClarificationAsk`, `SafetyVerdict`)
validate that reasoning is present. A decision without a why is not a decision,
it is a shrug, and the product is built on showing the why.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class Availability(str, Enum):
    """Reachability, independent of asleep/awake.

    A neighbour can be home-but-asleep (available, asleep), out while their
    stock still exists (not_at_home), or home and awake (available).
    """

    AVAILABLE = "available"
    BUSY = "busy"
    NOT_AT_HOME = "not_at_home"


class Urgency(str, Enum):
    LOW = "low"
    HIGH = "high"
    EMERGENCY = "emergency"


class SafetyStatus(str, Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"
    NEEDS_CHECK = "needs_check"
    UNASSESSED = "unassessed"


class OfferStatus(str, Enum):
    PROPOSED = "proposed"
    DECLINED = "declined"
    VETOED = "vetoed"
    RELEASED = "released"
    ACCEPTED = "accepted"


class HandoverState(str, Enum):
    PROPOSED = "proposed"
    AGREED = "agreed"
    COLLECTED = "collected"
    RELEASED = "released"
    EXPIRED = "expired"


class RequestStatus(str, Enum):
    PARSED = "parsed"
    OUTREACH = "outreach"
    AWAITING_CHOICE = "awaiting_choice"
    AWAITING_PICKUP = "awaiting_pickup"
    FULFILLED = "fulfilled"
    NO_MATCH = "no_match"
    CANCELLED = "cancelled"


class LedgerDirection(str, Enum):
    """Who owes whom.

    `MARYAM_OWES` — Maryam borrowed; she owes the neighbour.
    `NEIGHBOUR_OWES` — Maryam lent; the neighbour owes her.
    """

    MARYAM_OWES = "maryam_owes"
    NEIGHBOUR_OWES = "neighbour_owes"


class ThreadRole(str, Enum):
    NEAR_MIND = "near_mind"
    NEIGHBOUR = "neighbour"
    MARYAM = "maryam"


class LogAction(str, Enum):
    PARSED_REQUEST = "parsed_request"
    SKIPPED_NEIGHBOUR = "skipped_neighbour"
    OUTREACH_SENT = "outreach_sent"
    REPLY_TRANSLATED = "reply_translated"
    CLARIFICATION_ASKED = "clarification_asked"
    SAFETY_ASSESSED = "safety_assessed"
    SAFETY_VETO = "safety_veto"
    OFFER_RELAYED = "offer_relayed"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_RELEASED = "offer_released"
    HANDOVER_PROPOSED = "handover_proposed"
    HANDOVER_AGREED = "handover_agreed"
    HANDOVER_COLLECTED = "handover_collected"
    HANDOVER_EXPIRED = "handover_expired"
    HANDOVER_PIVOTED = "handover_pivoted"
    URGENCY_OVERRIDE = "urgency_override"
    NO_MATCH = "no_match"
    RECIPROCITY_SUGGESTED = "reciprocity_suggested"
    RECIPROCITY_CONFIRMED = "reciprocity_confirmed"
    AVAILABILITY_CHANGED = "availability_changed"
    SCHEMA_REPAIRED = "schema_repaired"
    SCHEMA_REJECTED = "schema_rejected"
    MODEL_CALL_FAILED = "model_call_failed"
    INBOUND_IGNORED = "inbound_ignored"


class Actor(str, Enum):
    NEAR_MIND = "near_mind"
    NEIGHBOUR = "neighbour"
    MARYAM = "maryam"
    SYSTEM = "system"


# --------------------------------------------------------------------------- #
# Geo / prose
# --------------------------------------------------------------------------- #


class Wait(BaseModel):
    """'Give me 5' — a neighbour asking for time before they can look."""

    model_config = ConfigDict(extra="forbid")

    minutes: int = Field(ge=0, le=24 * 60)
    note: str = ""


class SafetyVerdict(BaseModel):
    """The result of assessing an item before it is ever put in front of Maryam.

    `reason` is mandatory: a verdict that says what without a why is useless
    to the log and to the user.
    """

    model_config = ConfigDict(extra="forbid")

    status: SafetyStatus = SafetyStatus.UNASSESSED
    reason: str = Field(min_length=1)
    hazards: list[str] = Field(default_factory=list)
    requires_condition: str | None = None

    @model_validator(mode="after")
    def _veto_needs_hazard(self) -> SafetyVerdict:
        if self.status is SafetyStatus.UNSAFE and not self.hazards:
            raise ValueError("an unsafe verdict must name at least one hazard")
        if self.status is SafetyStatus.NEEDS_CHECK and not self.requires_condition:
            raise ValueError("a needs_check verdict must say what to check")
        return self


class InventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str
    quantity: float = Field(default=1.0, ge=0)
    unit: str = "pcs"
    condition: str = "good"
    tags: list[str] = Field(default_factory=list)
    # Anything the safety layer must reason about. Never guessed at runtime.
    attributes: dict[str, str] = Field(default_factory=dict)

    def matches(self, item: str, substitutes: list[str]) -> str | None:
        """Which requested token this item satisfies, or None."""
        key = item.strip().lower()
        if self.item.strip().lower() == key:
            return self.item
        for sub in substitutes:
            if self.item.strip().lower() == sub.strip().lower():
                return self.item
        return None


class MemoryNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at: datetime
    note: str


class Neighbour(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    house_number: str
    name: str
    personality: str
    texting_style: str
    inventory: list[InventoryItem] = Field(default_factory=list)
    sleep_window: tuple[str, str] = ("22:00", "07:00")
    clock_offset_minutes: int = 0
    fairness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    memory: list[MemoryNote] = Field(default_factory=list)
    is_real: bool = False

    @property
    def label(self) -> str:
        return f"{self.name} (#{self.house_number})"


class Maryam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = "maryam"
    house_number: str = "10"
    name: str = "Maryam"


# --------------------------------------------------------------------------- #
# Availability
# --------------------------------------------------------------------------- #


class AvailabilityState(BaseModel):
    """Why a neighbour is in the state they are in, and since when."""

    model_config = ConfigDict(extra="forbid")

    state: Availability = Availability.AVAILABLE
    reason: str = Field(min_length=1)
    since: datetime
    set_by: Literal["sandbox", "whatsapp", "system"] = "sandbox"
    # Set when the state expires on its own (BUSY windows).
    expires_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #


class ParsedIntent(BaseModel):
    """What the user meant. Produced by the model, validated by schema."""

    model_config = ConfigDict(extra="forbid")

    item: str = Field(min_length=1)
    quantity: float = Field(default=1.0, gt=0)
    unit: str = "pcs"
    urgency: Urgency = Urgency.LOW
    substitutes: list[str] = Field(default_factory=list)
    safety_attributes: list[str] = Field(default_factory=list)
    purpose: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _dedupe(self) -> ParsedIntent:
        seen: list[str] = []
        for s in self.substitutes:
            s = s.strip()
            if s and s.lower() != self.item.lower() and s not in seen:
                seen.append(s)
        self.substitutes = seen
        self.safety_attributes = list(dict.fromkeys(a.strip() for a in self.safety_attributes if a.strip()))
        return self


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    message: str
    created_at: datetime
    clock_time: str
    intent: ParsedIntent
    status: RequestStatus = RequestStatus.PARSED
    # Closure text shown to the user when no match exists.
    closure: str | None = None


# --------------------------------------------------------------------------- #
# Offers
# --------------------------------------------------------------------------- #


class Offer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    request_id: str
    neighbour_id: str
    item: str
    quantity: float = Field(gt=0)
    unit: str = "pcs"
    condition: str = "good"
    status: OfferStatus = OfferStatus.PROPOSED
    safety: SafetyVerdict
    terms: str = "free, just bring it back"
    created_at: datetime
    # Rank used for the recommendation and for pivot ordering.
    score: float = 0.0
    reason: str = Field(min_length=1)


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offer_id: str | None = None
    summary: str = ""
    reason: str = Field(min_length=1)


# --------------------------------------------------------------------------- #
# Handover
# --------------------------------------------------------------------------- #


class Handover(BaseModel):
    """proposed → agreed → collected → released, with an expiry.

    The expiry is not optional: Maryam must never be left waiting because a
    neighbour said "give me 5" and vanished.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    request_id: str
    offer_id: str
    neighbour_id: str
    state: HandoverState = HandoverState.PROPOSED
    created_at: datetime
    expires_at: datetime
    agreed_at: datetime | None = None
    collected_at: datetime | None = None
    released_at: datetime | None = None
    checked_back_at: datetime | None = None
    history: list[tuple[HandoverState, datetime, str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _expiry_after_create(self) -> Handover:
        if self.expires_at <= self.created_at:
            raise ValueError("handover expiry must be after creation")
        return self

    @property
    def is_open(self) -> bool:
        return self.state in (HandoverState.PROPOSED, HandoverState.AGREED)

    def expired(self, now: datetime) -> bool:
        return self.is_open and now >= self.expires_at


def default_expiry(created_at: datetime, minutes: int = 20) -> datetime:
    """15–30 minute rule. 20 is the default; callers may tighten it."""
    minutes = max(15, min(30, minutes))
    return created_at + timedelta(minutes=minutes)


# --------------------------------------------------------------------------- #
# Ledger
# --------------------------------------------------------------------------- #


class LedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    direction: LedgerDirection
    neighbour_id: str
    item: str
    request_id: str | None = None
    note: str = ""
    settled: bool = False
    created_at: datetime
    settled_at: datetime | None = None


class ReciprocitySuggestion(BaseModel):
    """A suggestion, never a forced decision. Maryam confirms or drops it."""

    model_config = ConfigDict(extra="forbid")

    neighbour_id: str
    direction: LedgerDirection
    open_count: int = Field(ge=1)
    summary: str
    reason: str = Field(min_length=1)
    suggested: bool = True


# --------------------------------------------------------------------------- #
# Threads and messages
# --------------------------------------------------------------------------- #


class ThreadMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    thread_id: str
    role: ThreadRole
    text: str
    at: datetime
    # The neighbour's own words are kept verbatim; the translation sits
    # alongside so the split view can prove nothing leaked.
    translated: str | None = None
    schema_ok: bool = True


class Thread(BaseModel):
    """One isolated conversation per neighbour. Nothing crosses threads."""

    model_config = ConfigDict(extra="forbid")

    id: str
    neighbour_id: str
    request_id: str
    messages: list[ThreadMessage] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Decision log
# --------------------------------------------------------------------------- #


class DecisionLog(BaseModel):
    """What NearMind did, and — mandatorily — why."""

    model_config = ConfigDict(extra="forbid")

    id: str
    at: datetime
    clock_time: str
    actor: Actor = Actor.NEAR_MIND
    action: LogAction
    reason: str
    neighbours: list[str] = Field(default_factory=list)
    request_id: str | None = None
    entities: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _reason_required(self) -> DecisionLog:
        if not self.reason or not self.reason.strip():
            raise ValueError("a decision log entry requires a non-empty reason")
        return self


# --------------------------------------------------------------------------- #
# Progress / streaming log
# --------------------------------------------------------------------------- #


class ProgressEvent(BaseModel):
    """Feeds the UI's live progress badge + streaming log."""

    model_config = ConfigDict(extra="forbid")

    at: datetime
    stage: str
    message: str
    done: bool = False
