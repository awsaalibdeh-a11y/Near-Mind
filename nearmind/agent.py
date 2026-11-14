"""The NearMind agent flow.

    parse → eligibility → outreach → read replies → clarify → safety
          → offers + recommendation → choice → handover → release / closure

Every step that decides something writes a `DecisionLog` with the reason.
Every model call goes through `ValidatingModel`, so a model going off-script
cannot reach state — the worst it can do is force a clarifying question.

The flow is expressed as small numbered steps rather than one long method so
each rule can be tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import eligibility as elig
from . import handover as ho
from . import ledger as led
from . import safety
from .clock import human_window
from .llm import ValidatingModel
from .models import (
    Actor,
    Availability,
    HandoverState,
    LedgerDirection,
    LogAction,
    Offer,
    OfferStatus,
    ParsedIntent,
    Recommendation,
    Request,
    RequestStatus,
    SafetyStatus,
    SafetyVerdict,
    Thread,
    ThreadRole,
    Urgency,
)
from .safety import is_usable
from .schemas import SchemaOutcome
from .world import World, new_id


@dataclass
class FlowResult:
    request: Request
    offers: list[Offer] = field(default_factory=list)
    recommendation: Recommendation | None = None
    closure: str | None = None
    skipped: list[dict] = field(default_factory=list)
    schema_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "request": self.request.model_dump(mode="json"),
            "offers": [o.model_dump(mode="json") for o in self.offers],
            "recommendation": (
                self.recommendation.model_dump(mode="json") if self.recommendation else None
            ),
            "closure": self.closure,
            "skipped": self.skipped,
            "schema_failures": self.schema_failures,
        }


class Agent:
    def __init__(self, world: World, model) -> None:
        self.world = world
        self.model = ValidatingModel(model)

    # ------------------------------------------------------------------ #
    # 1. Parse
    # ------------------------------------------------------------------ #

    def _parse(self, message: str) -> tuple[ParsedIntent, bool]:
        self.world.progress_event("parse", "Reading what you asked for…")
        outcome, raw = self.model.parse_intent(message)
        if outcome.ok:
            schema = outcome.model
            intent = ParsedIntent(
                item=schema.item,
                quantity=schema.quantity,
                unit=schema.unit,
                urgency=schema.urgency,
                substitutes=schema.substitutes,
                safety_attributes=schema.safety_attributes,
                purpose=schema.purpose,
                confidence=schema.confidence,
            )
            self.world.log(
                action=LogAction.PARSED_REQUEST,
                reason=(
                    f"Read the request as {intent.quantity:g}{intent.unit} {intent.item}, "
                    f"urgency {intent.urgency.value}, substitutes "
                    f"{', '.join(intent.substitutes) or 'none'}."
                ),
                entities={"message": message[:200]},
            )
            if outcome.repaired:
                self._note_schema("Intent", outcome, repaired=True)
            return intent, True

        # Graceful degradation: fall back to a conservative reading.
        self._note_schema("Intent", outcome)
        fallback = ParsedIntent(
            item=self._guess_item(message),
            quantity=1.0,
            unit="pcs",
            urgency=Urgency.LOW,
            substitutes=[],
            confidence=0.1,
        )
        self.world.log(
            action=LogAction.MODEL_CALL_FAILED,
            reason=(
                "Intent parsing did not return a valid schema; fell back to a "
                f"conservative reading ({fallback.item}, urgency low, no substitutes). "
                "Nothing was guessed beyond that, so a bad reply cannot inflate a request."
            ),
            entities={"error": (outcome.error or "")[:300]},
        )
        return fallback, False

    def _guess_item(self, message: str) -> str:
        words = [w for w in message.replace("?", " ").split() if len(w) > 2]
        return words[-1].strip(",.").lower() if words else "an unknown item"

    def _note_schema(self, where: str, outcome: SchemaOutcome, repaired: bool = False) -> None:
        parsed = outcome.model
        self.world.stats["schema_failures"] += 1
        self.world.log(
            action=LogAction.SCHEMA_REPAIRED if repaired else LogAction.SCHEMA_REJECTED,
            reason=(
                f"{where} model output "
                + ("was repaired losslessly and accepted." if repaired else "did not validate; the step downgraded instead of guessing.")
            ),
            entities={"error": (outcome.error or "")[:300], "raw": (outcome.raw or "")[:300]},
        )
        if isinstance(parsed, type(None)):
            return

    # ------------------------------------------------------------------ #
    # 2. Eligibility
    # ------------------------------------------------------------------ #

    def _eligible(self, intent: ParsedIntent, request_id: str) -> tuple[list[elig.Eligibility], list[dict]]:
        self.world.progress_event("eligibility", "Checking schedules and availability…")
        candidates: list[elig.Eligibility] = []
        skipped: list[dict] = []
        for nid in self.world.neighbours:
            neighbour = self.world.neighbour(nid)
            verdict = elig.assess(neighbour, intent, self.world)
            if verdict.eligible:
                candidates.append(verdict)
            else:
                skipped.append({"neighbour_id": nid, "reason": verdict.reason})
                self.world.log(
                    action=LogAction.SKIPPED_NEIGHBOUR,
                    reason=verdict.reason,
                    neighbours=[nid],
                    request_id=request_id,
                )
                if self.world.is_asleep(neighbour) and intent.urgency is Urgency.LOW:
                    self.world.note_memory(nid, f"Did not wake them at {self.world.local_time(neighbour):%H:%M} for {intent.item}.")
        return elig.rank(candidates, self.world), skipped

    # ------------------------------------------------------------------ #
    # 3. Outreach
    # ------------------------------------------------------------------ #

    def _outreach(self, request: Request, candidates: list[elig.Eligibility]) -> list[Thread]:
        threads: list[Thread] = []
        intent = request.intent
        for cand in candidates:
            neighbour = self.world.neighbour(cand.neighbour_id)
            if cand.urgency_override and cand.needs_wake:
                self.world.stats["wakes"] += 1
                self.world.log(
                    action=LogAction.URGENCY_OVERRIDE,
                    reason=(
                        f"Deliberately waking {neighbour.label}: local time "
                        f"{self.world.local_time(neighbour):%H:%M} is inside their sleep "
                        f"window {human_window(neighbour.sleep_window)}, but urgency is "
                        f"{intent.urgency.value} ({intent.purpose or intent.item}). "
                        "This is an explicit override, not an accident."
                    ),
                    neighbours=[neighbour.id],
                    request_id=request.id,
                )

            thread = self.world.open_thread(request.id, neighbour.id)
            threads.append(thread)
            self.world.progress_event("outreach", f"Messaging {neighbour.name}…")

            outcome, raw = self.model.compose_outreach(
                neighbour, intent, self.world.clock.hhmm()
            )
            if outcome.ok:
                text = outcome.model.text  # type: ignore[union-attr]
            else:
                self._note_schema("Outreach", outcome)
                # Fall back to a neutral, truthful message — never skip outreach
                # just because the phrasing model failed.
                qty = f"{intent.quantity:g}{intent.unit}" if intent.unit != "pcs" else f"{intent.quantity:g}"
                text = (
                    f"Hi {neighbour.name.split()[0]}, Maryam from #10 is asking whether you "
                    f"have {qty} {intent.item} to lend. Thanks!"
                )
            self.world.post(thread, ThreadRole.NEAR_MIND, text)
            self.world.log(
                action=LogAction.OUTREACH_SENT,
                reason=(
                    f"Contacted {neighbour.label} in their style "
                    f"({neighbour.texting_style.split('.')[0].lower()}). {cand.reason}"
                ),
                neighbours=[neighbour.id],
                request_id=request.id,
                entities={"thread": thread.id},
            )
        return threads

    # ------------------------------------------------------------------ #
    # 4–5. Read replies, clarify, assess safety
    # ------------------------------------------------------------------ #

    def _read_and_offer(
        self,
        request: Request,
        candidates: list[elig.Eligibility],
        threads: list[Thread],
    ) -> tuple[list[Offer], list[str]]:
        intent = request.intent
        by_nid = {c.neighbour_id: c for c in candidates}
        offers: list[Offer] = []
        failures: list[str] = []

        for thread in threads:
            neighbour = self.world.neighbour(thread.neighbour_id)
            cand = by_nid[thread.neighbour_id]
            assert cand.item is not None

            reply_text, reading, failure = self._simulate_reply(neighbour, cand, intent)
            if failure:
                failures.append(failure)

            self.world.post(thread, ThreadRole.NEIGHBOUR, reply_text)
            if reading is not None:
                self.world.post(
                    thread,
                    ThreadRole.NEAR_MIND,
                    "(read)",
                    translated=self._describe_reading(reading),
                )
                self.world.log(
                    action=LogAction.REPLY_TRANSLATED,
                    reason=(
                        f"{neighbour.label} said “{reply_text}”. NearMind read that as: "
                        f"{self._describe_reading(reading)}."
                    ),
                    neighbours=[neighbour.id],
                    request_id=request.id,
                )

            # Unclear reply → one short clarifying question.
            if reading is not None and (reading.vague or reading.has_item is None or reading.question):
                question = self._clarify(neighbour, cand.item.item, reading, request)
                self.world.post(thread, ThreadRole.NEAR_MIND, question)
                continue

            if reading is not None and reading.decline:
                continue

            condition = (reading.condition if reading is not None and reading.condition else cand.item.condition)
            attributes = dict(cand.item.attributes)
            if reading is not None and reading.condition and reading.condition not in attributes.get("stability", ""):
                # The neighbour described a condition the inventory didn't hold.
                attributes.setdefault("reported_condition", reading.condition)

            verdict_outcome, raw = self.model.assess_safety(cand.item.item, attributes)
            if verdict_outcome.ok:
                model_verdict = SafetyVerdict(
                    status=verdict_outcome.model.status,  # type: ignore[union-attr]
                    reason=verdict_outcome.model.reason or "model returned no reason",  # type: ignore[union-attr]
                    hazards=verdict_outcome.model.hazards,  # type: ignore[union-attr]
                    requires_condition=verdict_outcome.model.requires_condition,  # type: ignore[union-attr]
                )
                if model_verdict.status is SafetyStatus.UNSAFE and not model_verdict.hazards:
                    model_verdict = SafetyVerdict(
                        status=SafetyStatus.NEEDS_CHECK,
                        reason=model_verdict.reason,
                        requires_condition="stability",
                    )
            else:
                self._note_schema("Safety", verdict_outcome)
                model_verdict = SafetyVerdict(
                    status=SafetyStatus.UNASSESSED,
                    reason="Safety model output was unusable; falling back to deterministic rules.",
                )

            verdict = safety.tighten(cand.item.item, condition, attributes, model_verdict)

            if not is_usable(verdict):
                if verdict.status is SafetyStatus.UNSAFE:
                    self.world.stats["vetoed"] += 1
                    other_holders = self._other_holders(request, exclude=neighbour.id)
                    existence_note = (
                        f"Nobody else has a replacement ({other_holders}), so the veto is "
                        "holding against scarcity pressure."
                        if other_holders
                        else "No other neighbour has a replacement either, and the veto still holds."
                    )
                    self.world.log(
                        action=LogAction.SAFETY_VETO,
                        reason=(
                            f"Rejected {neighbour.label}'s {cand.item.item} ({condition}): "
                            f"{', '.join(verdict.hazards)}. {verdict.reason} {existence_note}"
                        ),
                        neighbours=[neighbour.id],
                        request_id=request.id,
                        entities={"hazards": "; ".join(verdict.hazards)},
                    )
                    continue
                # needs_check → ask for the missing condition, don't offer yet.
                question = self._clarify(
                    neighbour,
                    cand.item.item,
                    _RequiresCondition(verdict.requires_condition or "condition"),
                    request,
                )
                self.world.post(thread, ThreadRole.NEAR_MIND, question)
                continue

            # The offer is always expressed in the unit the neighbour's stock is in.
            quantity = self._quantity_from(reading, cand.item.quantity, intent.quantity, intent.unit)
            offer = Offer(
                id=new_id("offer"),
                request_id=request.id,
                neighbour_id=neighbour.id,
                item=cand.item.item,
                quantity=quantity,
                unit=cand.item.unit,
                condition=condition,
                safety=verdict,
                terms="free — just bring it back" if neighbour.id != "ali" else "Free. Please return it clean.",
                created_at=self.world.now(),
                score=self._score(neighbour, verdict, cand),
                reason=(
                    f"{neighbour.label} has {cand.item.item} ({condition}) and it passed the "
                    f"safety check. {verdict.reason}"
                ),
            )
            self.world.offers[offer.id] = offer
            offers.append(offer)
            self.world.log(
                action=LogAction.SAFETY_ASSESSED,
                reason=f"{offer.item} from {neighbour.label}: safe. {verdict.reason}",
                neighbours=[neighbour.id],
                request_id=request.id,
                entities={"offer": offer.id},
            )

        offers.sort(key=lambda o: (-o.score, o.neighbour_id))
        return offers, failures

    def _other_holders(self, request: Request, exclude: str) -> str:
        names = []
        for nid, neighbour in self.world.neighbours.items():
            if nid == exclude:
                continue
            found = elig.find_item(neighbour, request.intent)
            if found:
                names.append(f"{neighbour.label}: {found[0].item} ({found[0].condition})")
        return "; ".join(names) if names else ""

    def _quantity_from(self, reading, available: float, wanted: float, unit: str) -> float:
        """How much of the stock is lent.

        Only a same-unit quantity from the neighbour can cap it; otherwise the
        whole stock (or the whole stock if Maryam wanted more) is offered.
        """
        offered = available
        if reading is not None and reading.quantity:
            reading_unit = (reading.unit or "").strip().lower()
            if not reading_unit or reading_unit == (unit or "").strip().lower():
                offered = min(available, reading.quantity)
        return max(0.0, offered)

    def _score(self, neighbour, verdict: SafetyVerdict, cand: elig.Eligibility) -> float:
        base = 1.0 if verdict.status is SafetyStatus.SAFE else 0.0
        if cand.requested_as and cand.requested_as.lower() != (cand.item.item if cand.item else "").lower():
            base -= 0.15  # substitute, slightly worse than exact
        base -= 0.05 if cand.needs_wake else 0.0
        base += 0.1 * (1.0 - neighbour.fairness_score)  # balance who Maryam leans on
        base += 0.02 * led.owed_by_maryam(self.world, neighbour.id)  # quiet reciprocity nudge
        base += 0.01 if (cand.item and cand.item.condition in ("good", "new")) else 0.0
        return round(base, 4)

    def _describe_reading(self, reading) -> str:
        bits = []
        if reading.decline:
            bits.append("a decline")
        if reading.has_item:
            bits.append(f"they have {reading.item or 'it'}")
        if reading.quantity:
            bits.append(f"quantity {reading.quantity:g}")
        if reading.condition:
            bits.append(f"condition “{reading.condition}”")
        if reading.wait_minutes is not None:
            bits.append(f"a wait of {reading.wait_minutes} min")
        if reading.question:
            bits.append(f"a question (“{reading.question}”)")
        if reading.vague:
            bits.append("vague — needs one clarification")
        return "; ".join(bits) or "nothing actionable"

    def _clarify(self, neighbour, item: str, reading, request: Request) -> str:
        missing = getattr(reading, "requires_condition", None) or "which one and how much"
        outcome, raw = self.model.compose_clarification(neighbour, item, str(missing))
        if outcome.ok:
            text = outcome.model.text  # type: ignore[union-attr]
        else:
            self._note_schema("Clarification", outcome)
            text = f"Sorry — could you confirm {missing} for the {item}?"
        self.world.log(
            action=LogAction.CLARIFICATION_ASKED,
            reason=(
                f"{neighbour.label}'s reply wasn't specific enough for {item} "
                f"({missing}). Asked one short question instead of guessing — a wrong "
                "quantity here would end up in the ledger."
            ),
            neighbours=[neighbour.id],
            request_id=request.id,
        )
        return text

    def _simulate_reply(self, neighbour, cand, intent) -> tuple[str, object, str | None]:
        """Get the neighbour's words, then read them with the model.

        In the sandbox the neighbour's words are scripted on `World.nuances`
        (see `scenarios`). The reading always goes through the model + schema.
        """
        script = getattr(self.world, "reply_script", {})
        key = (cand.neighbour_id, intent.item.lower())
        reply_text = script.get(key)
        if reply_text is None:
            reply_text = self._default_reply(neighbour, cand, intent)

        outcome, raw = self.model.read_reply(reply_text, cand.item.item if cand.item else intent.item)
        if outcome.ok:
            return reply_text, outcome.model, None
        self._note_schema("Reply", outcome)
        return reply_text, None, (outcome.error or "invalid reply schema")

    def _default_reply(self, neighbour, cand, intent) -> str:
        if neighbour.id == "karim":
            return "yeah i've got some! grab it whenever"
        if neighbour.id == "ali":
            return f"We have it. When would you like to collect it?"
        if neighbour.id == "umm_samir":
            return "habibti of course... it's somewhere in the kitchen... give me 5 minutes"
        return "Yes, that's fine."

    # ------------------------------------------------------------------ #
    # 6. Recommendation
    # ------------------------------------------------------------------ #

    def _recommend(self, request: Request, offers: list[Offer]) -> Recommendation:
        if not offers:
            return Recommendation(
                offer_id=None,
                summary="",
                reason="No safe offer to recommend.",
            )
        best = offers[0]
        neighbour = self.world.neighbour(best.neighbour_id)
        alternatives = [o for o in offers[1:]]
        alt_note = (
            f" Alternative: {self.world.neighbour(alternatives[0].neighbour_id).name} also offered "
            f"{alternatives[0].item}." if alternatives else ""
        )
        rec = Recommendation(
            offer_id=best.id,
            summary=(
                f"{neighbour.name} has {_qty_text(best.quantity, best.unit)} {best.item} "
                f"({best.condition}). Best option: {best.terms.rstrip('.')}.{alt_note}"
            ),
            reason=(
                f"Ranked first: it is{' the exact item' if best.item.lower() == request.intent.item.lower() else ' an accepted substitute'}, "
                f"passed safety, and {neighbour.name} was awake and available. "
                f"Score {best.score:.2f}."
                + (" Second-best kept on standby in case of handover expiry." if alternatives else "")
            ),
        )
        self.world.log(
            action=LogAction.OFFER_RELAYED,
            reason=rec.reason,
            neighbours=[best.neighbour_id],
            request_id=request.id,
            entities={"offer": best.id, "recommended": best.id},
        )
        return rec

    # ------------------------------------------------------------------ #
    # Public: run the whole flow
    # ------------------------------------------------------------------ #

    def handle(self, message: str) -> FlowResult:
        intent, parsed_ok = self._parse(message)
        request = Request(
            id=new_id("req"),
            message=message,
            created_at=self.world.now(),
            clock_time=self.world.clock.hhmm(),
            intent=intent,
            status=RequestStatus.PARSED,
        )
        self.world.requests[request.id] = request
        self.world.stats["requests"] += 1

        candidates, skipped = self._eligible(intent, request.id)

        if not candidates:
            return self._no_match(request, skipped, [])

        request.status = RequestStatus.OUTREACH
        threads = self._outreach(request, candidates)

        offers, failures = self._read_and_offer(request, candidates, threads)
        if not offers:
            return self._no_match(request, skipped, failures)

        recommendation = self._recommend(request, offers)
        request.status = RequestStatus.AWAITING_CHOICE
        self.world.progress_event("recommend", "Found a safe option — relaying it to you.", done=True)
        return FlowResult(
            request=request,
            offers=offers,
            recommendation=recommendation,
            skipped=skipped,
            schema_failures=failures,
        )

    # ------------------------------------------------------------------ #
    # No-match closure
    # ------------------------------------------------------------------ #

    def _no_match(self, request: Request, skipped: list[dict], failures: list[str]) -> FlowResult:
        intent = request.intent
        request.status = RequestStatus.NO_MATCH
        self.world.stats["no_match"] += 1

        reasons = [s["reason"] for s in skipped]
        away = [s for s in skipped if "not at home" in s["reason"]]
        awake_with = self._anyone_with(intent, require_awake=True)

        # "The only holder is out" is its own, more specific no-match case.
        out_holders = [s["neighbour_id"] for s in away]
        if away and not awake_with:
            reason_text = "; ".join(
                f"{self.world.neighbour(nid).label} has it but {self._why_unreachable(nid)}"
                for nid in out_holders
            )
            closure = (
                f"Nobody who has {intent.item} is at home right now — {reason_text}. "
                "I'll let you know when they're back."
            )
        elif not awake_with:
            # Local alternatives are the honest fallback.
            alternatives = {
                "baking soda": "white vinegar or lemon juice works for most recipes",
                "salt": "soy sauce or stock cubes will carry the flavour",
                "sugar": "honey or a ripe banana, depending on what it's for",
                "ladder": "a sturdy chair is not a substitute — please wait for a proper ladder",
                "paracetamol": "this is medical — please ask the pharmacy or a neighbour who is home",
            }.get(intent.item.lower(), "")
            if alternatives:
                closure = (
                    f"Nobody is awake with {intent.item}, but {alternatives}."
                    if intent.urgency is Urgency.LOW
                    else f"Nobody is reachable with {intent.item} right now. {alternatives}."
                )
            else:
                closure = (
                    f"Nobody is reachable with {intent.item} right now. "
                    "I'll keep an eye out and let you know if something turns up."
                )
        else:
            detail = "; ".join(r.rstrip(".") for r in reasons[:2])
            closure = f"Nobody can help with {intent.item} right now — {detail}."

        if intent.urgency in (Urgency.HIGH, Urgency.EMERGENCY):
            closure += " If this becomes dangerous, call emergency services."

        request.closure = closure
        self.world.log(
            action=LogAction.NO_MATCH,
            reason=(
                f"No usable match for {intent.item} at {self.world.clock.hhmm()}. "
                f"{' '.join(reasons) if reasons else 'No safe offers were returned.'} "
                f"Closed with: {closure}"
            ),
            request_id=request.id,
            entities={"closure": closure},
        )
        self.world.progress_event("no_match", "No safe match — closing with an alternative.", done=True)
        return FlowResult(
            request=request,
            offers=[],
            recommendation=None,
            closure=closure,
            skipped=skipped,
            schema_failures=failures,
        )

    def _why_unreachable(self, neighbour_id: str) -> str:
        state = self.world.availability_of(neighbour_id)
        if state.state is Availability.NOT_AT_HOME:
            return f"is out ({state.reason})"
        if state.state is Availability.BUSY:
            return f"is busy ({state.reason})"
        return f"is asleep ({self.world.clock.hhmm()})"

    def _anyone_with(self, intent: ParsedIntent, require_awake: bool) -> list[str]:
        names = []
        for nid, neighbour in self.world.neighbours.items():
            if self.world.availability_of(nid).state is Availability.NOT_AT_HOME:
                continue
            if require_awake and self.world.is_asleep(neighbour):
                continue
            if elig.find_item(neighbour, intent):
                names.append(nid)
        return names

    # ------------------------------------------------------------------ #
    # Choice → handover → release others
    # ------------------------------------------------------------------ #

    def choose(self, request_id: str, offer_id: str) -> dict:
        request = self.world.requests[request_id]
        offer = self.world.offers[offer_id]
        if offer.request_id != request_id:
            raise ValueError("offer does not belong to this request")
        if not is_usable(offer.safety):
            raise ValueError("this offer was vetoed on safety grounds and cannot be accepted")

        offer.status = OfferStatus.ACCEPTED
        world = self.world

        # Reciprocity nudge if Maryam owes this neighbour — suggested, not forced.
        nudge = led.owed_by_maryam(world, offer.neighbour_id)
        if nudge:
            world.log(
                action=LogAction.RECIPROCITY_SUGGESTED,
                reason=(
                    f"Maryam now owes {world.neighbour(offer.neighbour_id).label} "
                    f"{nudge} favour{'s' if nudge != 1 else ''}. NearMind will prioritise this "
                    "neighbour's future reverse requests to help her pay it down."
                ),
                neighbours=[offer.neighbour_id],
                request_id=request_id,
            )

        world.log(
            action=LogAction.OFFER_ACCEPTED,
            reason=(
                f"Maryam accepted {world.neighbour(offer.neighbour_id).label}'s {offer.item}. "
                f"Safety passed ({offer.safety.reason}) and it was the top-ranked safe offer."
            ),
            neighbours=[offer.neighbour_id],
            request_id=request_id,
            entities={"offer": offer_id},
        )

        handover = ho.open_handover(world, request_id, offer)
        request.status = RequestStatus.AWAITING_PICKUP

        released = self._release_others(request_id, keep=offer.neighbour_id, request=request)
        return {
            "handover": handover.model_dump(mode="json"),
            "released": released,
        }

    def _release_others(self, request_id: str, keep: str, request: Request) -> list[dict]:
        """Release everyone politely — except the runner-up, who stays on standby.

        If the chosen neighbour ghosts, NearMind pivots to the runner-up instead
        of dead-ending. So the second-best offer is *not* sent away; it is told
        it is kept as a fallback, which is honest rather than a silent hold.
        """
        released: list[dict] = []
        others = [
            o
            for o in self.world.offers.values()
            if o.request_id == request_id
            and o.neighbour_id != keep
            and o.status is OfferStatus.PROPOSED
        ]
        others.sort(key=lambda o: (-o.score, o.neighbour_id))
        runner_up = others[0] if others else None

        for offer in others:
            neighbour = self.world.neighbour(offer.neighbour_id)
            thread = self._thread_for(request_id, offer.neighbour_id)
            if runner_up is not None and offer.id == runner_up.id:
                text = (
                    "thanks so much — Maryam's sorted for now, but if the other one "
                    "falls through could i come back to you? no pressure"
                )
                if thread is not None:
                    self.world.post(thread, ThreadRole.NEAR_MIND, text)
                self.world.log(
                    action=LogAction.OFFER_RELEASED,
                    reason=(
                        f"Released {neighbour.label} politely but kept them as the "
                        f"standby: Maryam took {self.world.neighbour(keep).label}'s offer, "
                        "and this is the next-best safe one if that handover expires."
                    ),
                    neighbours=[offer.neighbour_id],
                    request_id=request_id,
                    entities={"offer": offer.id, "standby": "true"},
                )
                released.append(
                    {"neighbour_id": offer.neighbour_id, "thread_message": text, "standby": True}
                )
                continue

            offer.status = OfferStatus.RELEASED
            text = (
                "thanks so much — Maryam's sorted now, no need to hold anything. "
                "will owe you one"
            )
            if thread is not None:
                self.world.post(thread, ThreadRole.NEAR_MIND, text)
            self.world.log(
                action=LogAction.OFFER_RELEASED,
                reason=(
                    f"Politely released {neighbour.label}: Maryam took "
                    f"{self.world.neighbour(keep).label}'s offer instead. "
                    "Nobody is left holding an item or wondering."
                ),
                neighbours=[offer.neighbour_id],
                request_id=request_id,
                entities={"offer": offer.id},
            )
            released.append({"neighbour_id": offer.neighbour_id, "thread_message": text})
        return released

    def _thread_for(self, request_id: str, neighbour_id: str) -> Thread | None:
        for t in self.world.threads_for(request_id):
            if t.neighbour_id == neighbour_id:
                return t
        return None

    # ------------------------------------------------------------------ #
    # Complete a handover (collection) — writes the ledger
    # ------------------------------------------------------------------ #

    def finish_handover(self, handover_id: str) -> dict:
        world = self.world
        handover = world.handovers[handover_id]
        offer = world.offers[handover.offer_id]
        # `complete` is idempotent-ish about *how* Maryam got here: if she
        # already agreed explicitly, don't re-agree.
        if handover.state is HandoverState.PROPOSED:
            ho.agree(world, handover)
        ho.collect(world, handover)
        ho.release(world, handover, note="collected and returned to Maryam")

        entry = world.add_ledger(
            LedgerDirection.MARYAM_OWES,
            handover.neighbour_id,
            offer.item,
            request_id=handover.request_id,
            note="from handover",
        )
        neighbour = world.neighbour(handover.neighbour_id)
        neighbour.fairness_score = min(1.0, neighbour.fairness_score + 0.05)
        world.note_memory(neighbour.id, f"Lent Maryam {offer.item}; she returned it.")
        request = world.requests[handover.request_id]
        request.status = RequestStatus.FULFILLED
        world.stats["fulfilled"] += 1
        world.log(
            action=LogAction.HANDOVER_COLLECTED,
            reason=(
                f"{neighbour.label}'s {offer.item} collected and returned. Recorded one "
                f"favour owed to {neighbour.name}; {neighbour.name}'s fairness score rose "
                f"to {neighbour.fairness_score:.2f} because they helped."
            ),
            neighbours=[neighbour.id],
            request_id=handover.request_id,
            entities={"handover": handover_id, "ledger": entry.id},
        )
        return {"handover": handover.model_dump(mode="json"), "ledger": entry.model_dump(mode="json")}


def _qty_text(quantity: float, unit: str) -> str:
    q = int(quantity) if float(quantity).is_integer() else quantity
    if unit in ("pcs", ""):
        return f"{q}"
    return f"{q}{unit}" if unit in {"kg", "g", "ml", "l"} else f"{q} {unit}"


class _RequiresCondition:
    """Tiny adapter so `_clarify` can take a plain string as the missing detail."""

    def __init__(self, value: str) -> None:
        self.requires_condition = value
