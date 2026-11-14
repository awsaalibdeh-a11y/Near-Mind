"""The neighbourhood world: clock, neighbours, threads, ledger, logs.

One `World` instance is the whole mutable state. Everything else in the package
is a pure function over it (or a thin service). That makes the invariants
testable and the API a thin adapter.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .clock import VirtualClock, human_window, in_sleep_window
from .config import Settings, seed_neighbours
from .models import (
    Actor,
    Availability,
    AvailabilityState,
    DecisionLog,
    Handover,
    InventoryItem,
    LedgerEntry,
    LedgerDirection,
    LogAction,
    Maryam,
    Neighbour,
    Offer,
    ProgressEvent,
    ReciprocitySuggestion,
    Request,
    Thread,
    ThreadMessage,
    ThreadRole,
    Wait,
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class World:
    settings: Settings
    clock: VirtualClock
    maryam: Maryam = field(default_factory=Maryam)
    neighbours: dict[str, Neighbour] = field(default_factory=dict)
    availability: dict[str, AvailabilityState] = field(default_factory=dict)
    threads: dict[str, Thread] = field(default_factory=dict)
    requests: dict[str, Request] = field(default_factory=dict)
    offers: dict[str, Offer] = field(default_factory=dict)
    handovers: dict[str, Handover] = field(default_factory=dict)
    ledger: list[LedgerEntry] = field(default_factory=list)
    logs: list[DecisionLog] = field(default_factory=list)
    progress: list[ProgressEvent] = field(default_factory=list)
    nuances: list[Wait] = field(default_factory=list)
    stats: dict[str, int] = field(
        default_factory=lambda: {
            "requests": 0,
            "fulfilled": 0,
            "no_match": 0,
            "vetoed": 0,
            "wakes": 0,
            "schema_failures": 0,
        }
    )

    # -- construction -------------------------------------------------------

    @classmethod
    def sandbox(cls, settings: Settings | None = None) -> "World":
        settings = settings or Settings()
        world = cls(settings=settings, clock=VirtualClock(settings.start_time))
        for entry in seed_neighbours(settings.third_neighbour_name):
            neighbour = Neighbour(
                id=entry["id"],
                house_number=entry["house_number"],
                name=entry["name"],
                personality=entry["personality"],
                texting_style=entry["texting_style"],
                inventory=[InventoryItem(**item) for item in entry["inventory"]],
                sleep_window=tuple(entry["sleep_window"]),  # type: ignore[arg-type]
                clock_offset_minutes=entry.get("clock_offset_minutes", 0),
                fairness_score=entry.get("fairness_score", 0.5),
            )
            world.neighbours[neighbour.id] = neighbour
            world.availability[neighbour.id] = AvailabilityState(
                state=Availability.AVAILABLE,
                reason="Sandbox default: at home and awake",
                since=world.clock.now(),
                set_by="sandbox",
            )
        return world

    # -- time ---------------------------------------------------------------

    def now(self) -> datetime:
        return self.clock.now()

    def tick(self, minutes: float) -> datetime:
        """Advance time and let any expiry-based rules fire."""
        self.clock.advance(minutes=minutes)
        self.expire_availability()
        return self.clock.now()

    # -- neighbours ---------------------------------------------------------

    def neighbour(self, neighbour_id: str) -> Neighbour:
        try:
            return self.neighbours[neighbour_id]
        except KeyError as exc:
            raise KeyError(f"unknown neighbour {neighbour_id!r}") from exc

    def local_time(self, neighbour: Neighbour) -> datetime:
        return self.clock.local(neighbour.clock_offset_minutes)

    def is_asleep(self, neighbour: Neighbour) -> bool:
        return in_sleep_window(self.local_time(neighbour), neighbour.sleep_window)

    def availability_of(self, neighbour_id: str) -> AvailabilityState:
        self.expire_availability()
        return self.availability[neighbour_id]

    def set_availability(
        self,
        neighbour_id: str,
        state: Availability,
        reason: str,
        *,
        set_by: str = "sandbox",
        minutes: int | None = None,
    ) -> AvailabilityState:
        """Change availability, logging the why. BUSY windows expire on their own."""
        neighbour = self.neighbour(neighbour_id)
        now = self.now()
        expires_at = None
        if minutes is not None:
            expires_at = now + timedelta(minutes=minutes)
        previous = self.availability[neighbour_id]
        self.availability[neighbour_id] = AvailabilityState(
            state=state,
            reason=reason,
            since=now,
            set_by=set_by,  # type: ignore[arg-type]
            expires_at=expires_at,
        )
        self.log(
            actor=Actor.SYSTEM if set_by == "system" else Actor.NEAR_MIND,
            action=LogAction.AVAILABILITY_CHANGED,
            reason=(
                f"{neighbour.label} moved {previous.state.value} → {state.value}: {reason}."
                + (f" Busy window auto-expires at {expires_at.strftime('%H:%M')}." if expires_at else "")
            ),
            neighbours=[neighbour_id],
            entities={"from": previous.state.value, "to": state.value, "set_by": set_by},
        )
        return self.availability[neighbour_id]

    def expire_availability(self) -> list[str]:
        """Lift expired BUSY windows. Sandbox/WhatsApp states without a window stay."""
        now = self.now()
        lifted: list[str] = []
        for neighbour_id, state in list(self.availability.items()):
            if state.expires_at is not None and now >= state.expires_at:
                neighbour = self.neighbours[neighbour_id]
                self.availability[neighbour_id] = AvailabilityState(
                    state=Availability.AVAILABLE,
                    reason=f"Busy window ended at {state.expires_at.strftime('%H:%M')}; back to available",
                    since=now,
                    set_by="system",
                )
                lifted.append(neighbour_id)
                self.log(
                    actor=Actor.SYSTEM,
                    action=LogAction.AVAILABILITY_CHANGED,
                    reason=(
                        f"{neighbour.label} is available again: their busy window "
                        f"('{state.reason}') expired at {state.expires_at.strftime('%H:%M')}."
                    ),
                    neighbours=[neighbour_id],
                    entities={"from": "busy", "to": "available"},
                )
        return lifted

    def sleep_window_label(self, neighbour: Neighbour) -> str:
        return human_window(neighbour.sleep_window)

    def note_memory(self, neighbour_id: str, note: str) -> None:
        neighbour = self.neighbour(neighbour_id)
        from .models import MemoryNote

        neighbour.memory.append(MemoryNote(at=self.now(), note=note))

    # -- logs ---------------------------------------------------------------

    def log(
        self,
        *,
        action: LogAction,
        reason: str,
        actor: Actor = Actor.NEAR_MIND,
        neighbours: list[str] | None = None,
        request_id: str | None = None,
        entities: dict[str, str] | None = None,
    ) -> DecisionLog:
        entry = DecisionLog(
            id=new_id("log"),
            at=self.now(),
            clock_time=self.clock.hhmm(),
            actor=actor,
            action=action,
            reason=reason,
            neighbours=neighbours or [],
            request_id=request_id,
            entities=entities or {},
        )
        self.logs.append(entry)
        return entry

    def progress_event(self, stage: str, message: str, done: bool = False) -> ProgressEvent:
        event = ProgressEvent(at=self.now(), stage=stage, message=message, done=done)
        self.progress.append(event)
        return event

    # -- threads -----------------------------------------------------------

    def open_thread(self, request_id: str, neighbour_id: str) -> Thread:
        thread = Thread(
            id=new_id("thread"),
            neighbour_id=neighbour_id,
            request_id=request_id,
        )
        self.threads[thread.id] = thread
        return thread

    def post(self, thread: Thread, role: ThreadRole, text: str, translated: str | None = None, schema_ok: bool = True) -> ThreadMessage:
        msg = ThreadMessage(
            id=new_id("msg"),
            thread_id=thread.id,
            role=role,
            text=text,
            at=self.now(),
            translated=translated,
            schema_ok=schema_ok,
        )
        thread.messages.append(msg)
        return msg

    def threads_for(self, request_id: str) -> list[Thread]:
        return [t for t in self.threads.values() if t.request_id == request_id]

    # -- ledger -------------------------------------------------------------

    def add_ledger(
        self,
        direction: LedgerDirection,
        neighbour_id: str,
        item: str,
        *,
        request_id: str | None = None,
        note: str = "",
    ) -> LedgerEntry:
        entry = LedgerEntry(
            id=new_id("led"),
            direction=direction,
            neighbour_id=neighbour_id,
            item=item,
            request_id=request_id,
            note=note,
            created_at=self.now(),
        )
        self.ledger.append(entry)
        return entry

    def open_ledger(self, direction: LedgerDirection | None = None) -> list[LedgerEntry]:
        return [e for e in self.ledger if not e.settled and (direction is None or e.direction is direction)]

    def settle_ledger(self, entry_id: str) -> LedgerEntry | None:
        for entry in self.ledger:
            if entry.id == entry_id and not entry.settled:
                entry.settled = True
                entry.settled_at = self.now()
                return entry
        return None

    # -- serialisation ------------------------------------------------------

    def snapshot(self) -> dict:
        """A JSON-safe view for the API and for the UI's inspector."""
        return {
            "clock": self.clock.hhmm(),
            "now": self.now().isoformat(),
            "maryam": self.maryam.model_dump(mode="json"),
            "neighbours": [self.neighbour_view(nid) for nid in self.neighbours],
            "stats": dict(self.stats),
        }

    def neighbour_view(self, neighbour_id: str) -> dict:
        neighbour = self.neighbour(neighbour_id)
        state = self.availability_of(neighbour_id)
        local = self.local_time(neighbour)
        return {
            "id": neighbour.id,
            "house_number": neighbour.house_number,
            "name": neighbour.name,
            "personality": neighbour.personality,
            "texting_style": neighbour.texting_style,
            "availability": state.model_dump(mode="json"),
            "asleep": self.is_asleep(neighbour),
            "sleep_window": list(neighbour.sleep_window),
            "local_time": local.strftime("%H:%M"),
            "fairness_score": round(neighbour.fairness_score, 3),
            "inventory": [inv.model_dump(mode="json") for inv in neighbour.inventory],
            "memory": [m.model_dump(mode="json") for m in neighbour.memory],
            "is_real": neighbour.is_real,
        }

    def to_json(self) -> str:
        return json.dumps(
            {
                "clock": self.now().isoformat(),
                "neighbours": {
                    nid: n.model_dump(mode="json") for nid, n in self.neighbours.items()
                },
                "availability": {
                    nid: a.model_dump(mode="json") for nid, a in self.availability.items()
                },
                "threads": {tid: t.model_dump(mode="json") for tid, t in self.threads.items()},
                "requests": {rid: r.model_dump(mode="json") for rid, r in self.requests.items()},
                "offers": {oid: o.model_dump(mode="json") for oid, o in self.offers.items()},
                "handovers": {hid: h.model_dump(mode="json") for hid, h in self.handovers.items()},
                "ledger": [e.model_dump(mode="json") for e in self.ledger],
                "logs": [l.model_dump(mode="json") for l in self.logs],
                "progress": [p.model_dump(mode="json") for p in self.progress],
                "stats": self.stats,
            },
            indent=2,
        )
