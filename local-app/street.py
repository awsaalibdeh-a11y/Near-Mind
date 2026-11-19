"""NearMind Street: ten AI neighbors in one building, any of them can ask, the robot on the roof routes everything.

Streams every step as an event so the web page can animate it:
  say     {from, to, text}        a message travelling neighbor -> robot or robot -> neighbor
  typing  {who, on}               someone is writing
  think   {text}                  what the robot decided this round
  parse   {item, kind, urgency}   what the robot understood the request to be
  status  {who, state}            asked | offer | no | chosen | released | asleep
  phase   {phase}                 understand | outreach | clarify | relay | handover | closed
  quick   {options}               tap-to-reply suggestions for the asker
  why     {who, text}             the robot's short reason for picking a neighbor
  ledger  {helped}                how often each neighbor has helped in this building (fairness)
  error   {error} / done
"""
from __future__ import annotations

import datetime
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, Response, request

ORDER = ["sedra", "osama", "sulaiman", "asma", "alwalid", "anas", "layla", "yousef", "noor", "hamza"]

# Public: what the robot knows (never the inventory). Hidden: what each neighbor really has and how they talk.
N = {
    "sedra": dict(name="Sedra", apt="1A", color="#ff7eb6", icon="🎬", style="bubbly & warm",
                  facts=["Into photography lately", "22, film student", "Loves movie nights, free most evenings", "Chatty, lots of emoji"],
                  sleep=(1.5, 9.0),
                  home="""You are Sedra, 22, film student in apartment 1A. Bubbly, warm, lots of emoji, lowercase. You call things by nicknames
("the big screen thing", "my popcorn baby"). At home: a mini projector + pull-down screen, a popcorn maker, a streaming subscription,
a bluetooth speaker, USB-C phone chargers, an extension cord, an umbrella, a bag of sugar. You LOVE company for movies and are free most
evenings. NO tools, NO ladder, NO eggs, NO first aid.
You'd happily BUY: a desk lamp, a bike, a film camera, cheap speakers. Budget: student, up to about 150 SAR."""),
    "osama": dict(name="Osama", apt="1B", color="#f2b560", icon="🧂", style="warm & proper",
                  facts=["Always upgrading his kitchen", "40s, cooks every day", "Generous with food, hates waste", "Prefers a polite ask"],
                  sleep=(23.5, 6.5),
                  home="""You are Osama, 40s, a keen home cook in apartment 1B. Warm, a little formal, says "my friend", describes things by use
("the salt I use for bread", "the good eggs from the farm"). At home: table salt and sea salt, sugar, flour, a dozen eggs, milk, rice,
spices, olive oil, mixing bowls, a rolling pin. NO tools, NO ladder, NO electronics to lend.
You'd happily BUY: a stand mixer, a cast-iron pan, good knives, an air fryer. Budget: fair prices, up to about 300 SAR."""),
    "sulaiman": dict(name="Sulaiman", apt="2A", color="#66b8ff", icon="🔧", style="short & practical",
                     facts=["Tinkers with old bikes and gadgets", "50s, retired mechanic", "Garage full of tools", "Few words, always returns calls"],
                     sleep=(22.0, 5.5),
                     home="""You are Sulaiman, 50s, retired mechanic in apartment 2A. Very few words, no emoji, practical ("the long one in the garage",
"got the 18 volt"). At home: a cordless drill, hammer, screwdriver set, wrench set, a 6ft aluminium step ladder, a 20m extension cord,
duct tape, a toolbox, work gloves. NO food to spare beyond tea, NO electronics.
You'd happily BUY: old bikes to fix, tool sets, a garden hose, car parts. Budget: haggles a little, up to about 200 SAR."""),
    "asma": dict(name="Asma", apt="2B", color="#8fe0c4", icon="🩹", style="calm & organised",
                 facts=["Setting up her new flat", "30s, nurse", "Very organised, keeps emergency supplies", "Early to bed (about 22:00)"],
                 sleep=(22.0, 6.0),
                 home="""You are Asma, 30s, a nurse in apartment 2B. Calm, organised, kind, complete sentences, practical safety advice when relevant.
At home: a full first aid kit, a thermometer, flashlights and spare batteries, candles, a power bank, an umbrella, tea, honey.
You never hand out prescription medicine. NO tools, NO ladder, NO baking ingredients.
You'd happily BUY: a bookshelf, house plants, a desk lamp, a coffee machine. Budget: up to about 250 SAR."""),
    "alwalid": dict(name="Alwalid", apt="3A", color="#a99bff", icon="🍲", style="chatty dad",
                    facts=["Kids grow out of everything", "30s, dad of three", "Busy at kids' bedtime (19:00-21:00)", "Big family movie nights on weekends"],
                    sleep=(23.0, 6.0),
                    home="""You are Alwalid, 30s, dad of three in apartment 3A. Chatty, friendly, mentions the kids, a bit chaotic ("the giant pot",
"the kids' stool"). At home: a huge cooking pot, folding chairs, a BBQ grill, eggs, milk, flour, a kids' step stool, umbrellas,
board games. Between 19:00 and 21:00 you are putting kids to bed and can only reply briefly. You enjoy family movies. NO power tools.
You'd happily BUY: kids' bikes, a scooter, board games, a stroller, toys. Budget: family, up to about 200 SAR."""),
    "anas": dict(name="Anas", apt="3B", color="#9aa7b1", icon="🎮", style="short & shy",
                 facts=["Building a gaming setup", "19, student", "Night owl: asleep roughly 04:00-12:00", "Keeps to himself, helps if asked nicely"],
                 sleep=(4.0, 12.0),
                 home="""You are Anas, 19, a shy student in apartment 3B. Very short replies, lowercase, a bit reluctant at first ("uh", "maybe"),
but kind when asked nicely. At home: a game console, an HDMI cable, phone chargers, a power bank, electrical tape, a step stool, instant
noodles. You like anime more than movies. NO tools beyond tape, NO food to spare, NO ladder.
You'd happily BUY: a gaming chair, a monitor, a controller, a headset, a desk. Budget: student, up to about 200 SAR."""),
    "layla": dict(name="Layla", apt="4A", color="#ff8a65", icon="🧵", style="gentle grandma",
                  facts=["Loves books and house plants", "60s, retired teacher, grandmother", "Sews and bakes, home most of the day", "Early to bed (about 21:30), up at dawn"],
                  sleep=(21.5, 5.5),
                  home="""You are Layla, 60s, a retired teacher and grandmother in apartment 4A. Gentle, unhurried, calls people "dear", full sentences.
At home: a sewing kit and sewing machine, thread and buttons, knitting needles, a cake tin, a hand mixer, flour, sugar, eggs, tea, a reading
lamp, lots of books, house plants, board games for the grandchildren. NO power tools, NO ladder, NO electronics to lend.
You'd happily BUY: books, house plants, a rocking chair, a good kettle. Budget: careful, up to about 150 SAR."""),
    "yousef": dict(name="Yousef", apt="4B", color="#26c6da", icon="🚴", style="upbeat & quick",
                   facts=["Into camping and cycling", "28, software engineer, works from home", "Has a car", "Night owl-ish, asleep about 00:30-07:30"],
                   sleep=(0.5, 7.5),
                   home="""You are Yousef, 28, a software engineer in apartment 4B. Upbeat, quick, a few emoji, says "easy" and "no worries".
At home: a bike pump and bike tools, a camping tent, a camping lantern, a cooler box, car jumper cables, laptop chargers (USB-C), an HDMI
cable, a portable speaker, an extension cord. You have a car and can give short rides. NO food to spare, NO ladder, NO first aid.
You'd happily BUY: camping gear, a bike rack, a standing desk, a bike. Budget: up to about 300 SAR."""),
    "noor": dict(name="Noor", apt="5A", color="#b5d96b", icon="🧁", style="sweet & lively",
                 facts=["Bakes for the whole floor", "26, pastry chef, early shifts", "Has a cat", "Asleep about 22:30-05:00"],
                 sleep=(22.5, 5.0),
                 home="""You are Noor, 26, a pastry chef in apartment 5A. Sweet and lively, talks about baking, a few emoji. At home: a stand mixer,
baking trays, cake tins, piping bags, butter, eggs, sugar, flour, vanilla, cocoa, a vacuum cleaner, a cat carrier, an umbrella.
Often has leftover pastries to share. NO tools, NO ladder, NO electronics to lend.
You'd happily BUY: a cast-iron pan, a bookshelf, a desk lamp, a cat tree. Budget: up to about 200 SAR."""),
    "hamza": dict(name="Hamza", apt="5B", color="#e48ad9", icon="⚽", style="sporty & direct",
                  facts=["Always looking for gym gear", "34, PE teacher and football coach", "Has a car", "Up early for the gym, asleep about 22:30-05:00"],
                  sleep=(22.5, 5.0),
                  home="""You are Hamza, 34, a PE teacher in apartment 5B. Direct, encouraging, coach energy ("let's go", "no problem bro").
At home: footballs and a ball pump, yoga mats, a folding table, a cooler box, car jumper cables, a wheelbarrow, a pressure washer,
a big first aid bag for the team, cones. You have a car. NO baking ingredients, NO ladder.
You'd happily BUY: a bike, dumbbells, a rowing machine, a gaming chair. Budget: up to about 250 SAR."""),
}

ROBOT_TMPL = """You are NearMind, the robot on the roof of {bname}, a ten-apartment building in {hood}. Every message between neighbors goes through you.
Each apartment is a family of 4-8 people; you talk to one contact person per apartment, who speaks for the household (family members may help).
Neighbors (id: name, apartment): {roster}.
One neighbor (the ASKER) asks you for something: an item to borrow, a small favor, company (e.g. someone to watch a movie with),
or they want to SELL something (with a price). For a sale, the ASKER is the seller and you look for a buyer.

How you work
1. Understand the request: item or company, quantity, urgency, sensible substitutes. If it's genuinely unclear, ask the asker one short question.
2. Pick the 1-3 neighbors (out of all ten; asking fewer people is better: never message everyone) most likely to have it AND be awake (use only the PUBLIC facts and clock below, never guess inventories),
   and ask each one briefly in their own style. Never ask the asker themselves. Ask 2 normally; 3 only when urgent or a long shot.
3. If a reply is vague ("the long thing in the garage"), ask THAT neighbor one short clarifying question before telling the asker.
4. Relay clear offers to the asker with a one-line recommendation and the reason (fastest, safest, awake, asked least) and ask which they want.
5. When the asker chooses, propose ONE concrete time and place yourself (e.g. "Hamza's door, 5B, in 10 minutes"), never an open
   question, and confirm it with the chosen neighbor; kindly release the others. As soon as the chosen neighbor agrees, confirm to the
   asker and set phase "closed". Don't ask the asker to confirm again.
Be decisive: aim to finish in about 3 rounds. Don't chase details that don't change the decision (which movie, photos, brand or
model). If a neighbor adds a condition ("if it's sturdy"), pass it to the asker once with your recommendation and let them decide.
Selling: pick the 1-3 neighbors whose PUBLIC facts suggest they would want it and ask if they are interested at the price. Relay interest
   (and any counter-offer) to the seller; never pressure anyone. When the seller picks a buyer, confirm with the buyer that the seller will
   bring it to the BUYER's door, payment on pickup, and close.

Rules
- Only relay what neighbors actually said. Never invent that someone has something.
- Privacy: never mention one neighbor's name or offer inside another neighbor's chat (except to the asker when relaying offers).
- Respect sleep: don't ping someone who is probably asleep unless it's urgent.
- Safety: mention plainly if an offer sounds unsafe and prefer the safer one.
- Kindness: never pass on insults, gossip or complaints about a neighbor, even if asked; say kindly that NearMind is only for
  favors and help, and contact nobody.
- Money: don't arrange money loans between neighbors and never ask anyone for card numbers, passwords or bank details; suggest
  family or a trusted friend instead (selling an item for a price is fine).
- Emergencies: if someone describes a real emergency (fire, injury, someone in danger), first tell them to call 911, then help.
- Keep every message to 1-2 short sentences, in the recipient's style.
- If nobody can help, tell the asker warmly and suggest an alternative.
- Fairness: don't lean on the same helpful neighbors every time. If two neighbors are about equally likely, ask the one who has
  helped or been asked less (see HELPED BEFORE below), and say so in "why" (e.g. "has one too, asked less").
- Language: write to each person in the language they use. If the asker writes in Arabic, write to the asker in Arabic and ask
  neighbors in Arabic too; otherwise use English. Keep names as they are.

Reply with ONE JSON object only:
{"think": str (one short sentence on what you are doing now, shown to the audience),
 "parse": {"item": str, "kind": "item"|"company"|"favor"|"sale", "qty": str, "price": str (sales only, e.g. "150 SAR"), "urgency": "low"|"medium"|"high"} or null (only when new or changed),
 "phase": "understand"|"outreach"|"clarify"|"relay"|"handover"|"closed",
 "status": {"<id>": "asked"|"offer"|"no"|"chosen"|"released"} (only entries that changed; in a sale "offer" = wants to buy, "chosen" = the buyer),
 "why": {"<id>": str} (ONLY in the round where you first ask someone: 3-7 words on why you picked them, from their PUBLIC facts and the clock, e.g. "has a car, up early"),
 "messages": [{"to": "<id>", "text": str}],
 "quick": [str] (0-3 short replies the asker could tap, only when your message to the asker asks a question)}"""


def robot_prompt(B):
    roster = ", ".join(f"{n}: {B['N'][n]['name']} {B['N'][n]['apt']}" for n in B["order"])
    return ROBOT_TMPL.replace("{bname}", B["name"]).replace("{hood}", B["hood_name"]).replace("{roster}", roster)

STATES = {"asked", "offer", "no", "chosen", "released"}
MAX_ASK = 3          # hard limit, in code: never more than 3 neighbors contacted per request, whatever the model or the asker says

import city                                               # noqa: E402  (needs N and ORDER above)
HOODS, BUILDINGS = city.build(N, ORDER)
for _h in HOODS:
    for _b in _h["buildings"]:
        BUILDINGS[_b]["hood_name"] = _h["name"]
for _B in BUILDINGS.values():
    _B["prompt"] = robot_prompt(_B)
ROBOT = BUILDINGS[city.FLAGSHIP]["prompt"]                # the flagship building's prompt (tests read this)


def valid_clock(clk):
    """'HH:MM' with a real time of day (00:00-23:59); anything else means "use the real clock"."""
    if len(clk) != 5 or clk[2] != ":" or not clk.replace(":", "").isdigit():
        return False
    return int(clk[:2]) < 24 and int(clk[3:]) < 60


def now_label(clock):
    if clock:
        h, m = (int(x) for x in clock.split(":"))
    else:
        n = datetime.datetime.now()
        h, m = n.hour, n.minute
    return f"{h:02d}:{m:02d}", h + m / 60


def asleep(nid, hf, NN=None):
    a, b = (NN or N)[nid]["sleep"]
    return (hf >= a or hf < b) if a > b else (a <= hf < b)


def new_session(bid=None):
    bid = bid if bid in BUILDINGS else city.FLAGSHIP
    return {"b": bid, "asker": None, "threads": {n: [] for n in BUILDINGS[bid]["order"]}, "brain": {}, "clock": None,
            "lock": threading.Lock(), "turns": 0, "ledger": {}}


def bld(S):
    return BUILDINGS[S.get("b") or city.FLAGSHIP]


def world(S):
    B = bld(S); NN = B["N"]
    label, hf = now_label(S["clock"])
    out = [f"CLOCK: {label}" + (" (simulated)" if S["clock"] else ""), "PUBLIC FACTS (you know nothing else about them):"]
    for n in B["order"]:
        st = "probably ASLEEP" if asleep(n, hf, NN) else "probably awake"
        out.append(f"- {n} ({NN[n]['name']} {NN[n].get('family', '')}, {NN[n]['apt']}, {NN[n]['style']}, household of {len(NN[n].get('members') or [1])}): {st}. "
                   + "; ".join(NN[n]["facts"]))
    led = {n: v for n, v in (S.get("ledger") or {}).items() if n in NN and n != S["asker"] and (v.get("asked") or v.get("helped"))}
    if led:
        out.append("HELPED BEFORE (earlier requests in this building; spread the load): " + "; ".join(
            f"{NN[n]['name']} asked {v.get('asked', 0)}x, helped {v.get('helped', 0)}x" for n, v in led.items()))
    out.append(f"ASKER: {S['asker']} ({NN[S['asker']]['name']})")
    return "\n".join(out)


def render(S):
    N = bld(S)["N"]
    out = []
    for n in bld(S)["order"]:
        th = S["threads"][n]
        if not th:
            continue
        out.append(f"[Chat: {N[n]['name']} <-> NearMind]" + (" (the ASKER)" if n == S["asker"] else ""))
        out += [f"{N[n]['name'] if w == 'me' else 'NearMind'}: {t}" for w, t in th]
        out.append("")
    return "\n".join(out) or "(no messages yet)"


def invented_offer(S, out, asker):
    """True when the robot reports or arranges an offer although no neighbor has said anything yet in this request.
    Code-level guard for the rule "only relay what neighbors actually said" (the model alone once broke it)."""
    phase = str(out.get("phase") or "")
    picks = any(st in ("offer", "chosen") for st in (out.get("status") or {}).values()) if isinstance(out.get("status"), dict) else False
    if phase not in ("relay", "handover") and not (phase == "closed" and picks):
        return False                              # asking, clarifying, or politely declining and closing: all fine
    to_asker = any(str(m.get("to", "")).lower() == asker for m in out.get("messages") or [] if isinstance(m, dict))
    anyone_replied = any(w == "me" for n, th in S["threads"].items() if n != asker for w, _ in th)
    return to_asker and not anyone_replied


def make_blueprint(chat, model, sim_model, sid_fn, public=False, gate=None):
    """gate(): optional check before each live run; returns an error text to refuse (rate limits on the public site)."""
    bp = Blueprint("street", __name__)
    SESS = {}

    def sess(sid, bid=city.FLAGSHIP):
        key = f"{sid}|{bid}"                              # one street per visitor per building
        if key not in SESS:
            if len(SESS) > 300:
                SESS.pop(next(iter(SESS)))
            SESS[key] = new_session(bid)
        return SESS[key]

    def loads(raw):
        try:
            return json.loads(raw)
        except Exception:
            a, b = raw.find("{"), raw.rfind("}")
            return json.loads(raw[a:b + 1])

    def robot(S, force):
        ctx = world(S) + "\n\n" + render(S) + "\nYour notes so far: " + json.dumps(S["brain"])
        if S.pop("nudge", None):
            ctx += ("\nCORRECTION: no neighbor has replied to you yet in this request, so you cannot report or recommend any offer. "
                    "Ask 1-3 neighbors first (or ask the asker one clarifying question), and wait for their answers.")
        if force:
            ctx += f"\nIMPORTANT: wrap up now. Send {bld(S)['N'][S['asker']]['name']} a message this round with what you know."
        msgs = [{"role": "system", "content": bld(S)["prompt"]}, {"role": "user", "content": ctx}]
        try:
            return loads(chat(msgs, json_mode=True, model=model))
        except Exception:
            return loads(chat(msgs, json_mode=True, model=model))

    def neighbor(S, nid):
        B = bld(S); N = B["N"]
        label, hf = now_label(S["clock"])
        mood = ""
        if B.get("flagship") and N[nid].get("members"):
            mood += (" You live with your family: " + "; ".join(f"{m['name']} ({m['role']}, {m['age']})" for m in N[nid]["members"][1:])
                     + ". Family members can help (e.g. a teenager can carry things), and you may mention them by name.")
        if asleep(nid, hf, N):
            mood = f" It is {label} and you were asleep: reply sleepy and short unless it's urgent."
        if B.get("flagship") and nid == "alwalid" and 19 <= hf < 21:
            mood += " You're putting the kids to bed: very brief."
        sys_ = (N[nid]["home"] + f"\nThe time is {label}." + mood +
                "\nReply in character to NearMind's latest message, 1-2 short sentences, plain text. Be truthful about what you have: you ONLY own the things listed above; "
                "if something isn't listed, you don't have it, so say no kindly. "
                "Your FIRST answer is a bit vague (nicknames, no exact types); get specific only when NearMind asks you to clarify. "
                f"Any time you suggest must be after {label} (later today, or tomorrow). Ask at most one question; if you're interested or can help, say so plainly. "
                "If asked to hand something over or join, agree and say when/how. If offered something for sale, decide honestly from what "
                "you'd buy and your budget; you may counter-offer politely. Reply in English, unless NearMind's latest message to you is in Arabic: then reply in Arabic. Never mention being an AI.")
        msgs = [{"role": "system", "content": sys_}]
        for w, t in S["threads"][nid]:
            msgs.append({"role": "user" if w == "ai" else "assistant", "content": t})
        return chat(msgs, model=sim_model, effort="minimal").strip().strip('"')

    def run(S, asker, text):
        N = bld(S)["N"]
        S["turns"] += 1
        if S["asker"] != asker or S["brain"].get("phase") == "closed":   # a new asker, or a new request after a closed one
            S["asker"], S["threads"], S["brain"] = asker, {n: [] for n in bld(S)["order"]}, {}
        S["threads"][asker].append(("me", text))
        yield {"t": "say", "from": asker, "to": "robot", "text": text}
        try:
            told, wrap = False, False                    # the asker always gets an answer, even when the robot declines
            for rnd in range(4):
                yield {"t": "typing", "who": "robot", "on": True}
                out = bp.robot_fn(S, rnd == 3 or wrap)
                if invented_offer(S, out, asker):         # reporting offers before anyone answered = making them up
                    S["nudge"] = True
                    out = bp.robot_fn(S, rnd == 3 or wrap)
                    if invented_offer(S, out, asker):     # still inventing: drop those messages rather than relay them
                        out = {"think": "Checking with neighbors before promising anything.", "phase": "outreach", "messages": []}
                yield {"t": "typing", "who": "robot", "on": False}
                if out.get("think"):
                    yield {"t": "think", "text": str(out["think"])[:200]}
                if isinstance(out.get("parse"), dict):
                    S["brain"]["parse"] = out["parse"]
                    p = out["parse"]
                    yield {"t": "parse", "item": str(p.get("item", ""))[:60], "kind": p.get("kind", "item"),
                           "urgency": p.get("urgency", ""), "qty": str(p.get("qty", ""))[:40], "price": str(p.get("price", "") or "")[:30]}
                if out.get("phase"):
                    S["brain"]["phase"] = str(out["phase"])
                    yield {"t": "phase", "phase": S["brain"]["phase"]}
                why = out.get("why") if isinstance(out.get("why"), dict) else {}
                for nid, reason in why.items():                  # the robot's reason for picking each neighbor, shown on screen
                    if nid in N and nid != asker and str(reason).strip():
                        yield {"t": "why", "who": nid, "text": str(reason).strip()[:60]}
                contacted = {n for n, th in S["threads"].items() if n != asker and th}
                def allowed(nid):                         # the 3-neighbor limit: someone new only while there is room
                    if nid in contacted or nid == asker:
                        return True
                    if len(contacted) < MAX_ASK:
                        contacted.add(nid)
                        return True
                    S["brain"]["limit"] = f"You may contact at most {MAX_ASK} neighbors per request; work with the ones you already asked."
                    return False
                for nid, st in (out.get("status") or {}).items():
                    if nid in N and st in STATES and nid != asker and (nid in contacted or (st == "asked" and allowed(nid))):
                        prev = S["brain"].setdefault("status", {}).get(nid)
                        S["brain"]["status"][nid] = st
                        led = S.setdefault("ledger", {}).setdefault(nid, {"asked": 0, "helped": 0})
                        if st == "asked" and prev is None:
                            led["asked"] += 1
                        if st == "chosen" and prev != "chosen":
                            led["helped"] += 1
                        yield {"t": "status", "who": nid, "state": st}
                to_asker, jobs = False, []
                for m in out.get("messages") or []:
                    nid, msg = str(m.get("to", "")).lower(), str(m.get("text", "")).strip()
                    if nid not in N or not msg or not allowed(nid):
                        continue
                    S["threads"][nid].append(("ai", msg))
                    yield {"t": "say", "from": "robot", "to": nid, "text": msg}
                    if nid == asker:
                        to_asker = True
                    else:
                        jobs.append(nid)
                if jobs:
                    for nid in jobs:
                        yield {"t": "typing", "who": nid, "on": True}
                    with ThreadPoolExecutor(3) as ex:
                        replies = list(ex.map(lambda n: (n, bp.neighbor_fn(S, n)), jobs))
                    for nid, rep in replies:
                        S["threads"][nid].append(("me", rep))
                        yield {"t": "typing", "who": nid, "on": False}
                        yield {"t": "say", "from": nid, "to": "robot", "text": rep}
                told = told or to_asker
                if not to_asker and not out.get("messages") and not told and not wrap and rnd < 3:
                    wrap = True                           # it sent nothing at all: one more round, told to answer the asker
                    continue
                if to_asker or not out.get("messages"):
                    q = [str(x)[:50] for x in (out.get("quick") or [])][:3]
                    if to_asker and q:
                        yield {"t": "quick", "options": q}
                    break
        except Exception as e:
            yield {"t": "error", "error": str(e)[:200]}
        helped = {n: v["helped"] for n, v in (S.get("ledger") or {}).items() if v.get("helped")}
        if helped:
            yield {"t": "ledger", "helped": helped}           # who has helped so far in this building (fairness)
        yield {"t": "done"}

    @bp.post("/api/street/run")
    def street_run():
        sid = sid_fn() or "me"
        d = request.get_json(force=True, silent=True)
        d = d if isinstance(d, dict) else {}             # bad JSON or a JSON list: treated as empty, so a clean 400
        bid = str(d.get("building") or city.FLAGSHIP)
        if bid not in BUILDINGS:
            return Response(json.dumps({"error": "unknown building"}), status=400, mimetype="application/json")
        S = sess(sid, bid)
        asker, text = str(d.get("from", "")).lower(), str(d.get("text", "")).strip()[:400]
        if asker not in BUILDINGS[bid]["N"] or not text:
            return Response(json.dumps({"error": "need a neighbor and a message"}), status=400, mimetype="application/json")
        clk = str(d.get("clock") or "")
        S["clock"] = clk if valid_clock(clk) else None
        refuse = "This street has had a lot of requests. Press Reset to start a fresh one." if public and S["turns"] >= 30 else None
        refuse = refuse or (gate() if gate else None)
        if refuse:
            return Response(json.dumps({"t": "error", "error": refuse}) + "\n" + json.dumps({"t": "done"}) + "\n",
                            mimetype="application/x-ndjson")

        def gen():
            if not S["lock"].acquire(blocking=False):
                yield json.dumps({"t": "error", "error": "NearMind is still busy with the last request"}) + "\n"
                yield json.dumps({"t": "done"}) + "\n"
                return
            try:
                for e in run(S, asker, text):
                    yield json.dumps(e, ensure_ascii=False) + "\n"
            finally:
                S["lock"].release()
        return Response(gen(), mimetype="application/x-ndjson", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @bp.post("/api/street/reset")
    def street_reset():
        d = request.get_json(force=True, silent=True)
        d = d if isinstance(d, dict) else {}
        SESS.pop(f"{sid_fn() or 'me'}|{d.get('building') or city.FLAGSHIP}", None)
        return {"ok": True}

    @bp.get("/api/street/people")
    def street_people():
        bid = request.args.get("b") or city.FLAGSHIP
        if bid not in BUILDINGS:
            return Response(json.dumps({"error": "unknown building"}), status=404, mimetype="application/json")
        B = BUILDINGS[bid]; NN = B["N"]
        label, hf = now_label(None)
        public = ("name", "family", "apt", "color", "icon", "style", "facts", "sleep", "members")
        people = {n: {k: NN[n][k] for k in public if k in NN[n]} | {"asleep": asleep(n, hf, NN),
                  "img": f"/static/img/{n}.webp" if B.get("flagship") else None} for n in B["order"]}
        return {"order": B["order"], "people": people, "building": {"id": bid, "name": B["name"], "hood": B["hood"],
                "hood_name": B["hood_name"], "flagship": bool(B.get("flagship"))}}

    @bp.get("/api/city")
    def city_map():
        out = []
        for h in HOODS:
            bs = []
            for bid in h["buildings"]:
                B = BUILDINGS[bid]
                bs.append({"id": bid, "name": B["name"], "flagship": bool(B.get("flagship")), "homes": len(B["order"]),
                           "people": sum(len(B["N"][n].get("members") or [1]) for n in B["order"]),
                           "families": [B["N"][n].get("family", "") for n in B["order"]]})
            out.append({k: h[k] for k in ("id", "name", "icon", "color", "desc")} | {"buildings": bs,
                       "people": sum(b["people"] for b in bs), "homes": sum(b["homes"] for b in bs)})
        return {"name": "NearMind City", "hoods": out, "buildings": sum(len(h["buildings"]) for h in out),
                "homes": sum(h["homes"] for h in out), "people": sum(h["people"] for h in out)}

    bp.run = run              # exposed for tests
    bp.sess = sess
    bp.robot_fn = robot
    bp.neighbor_fn = neighbor
    return bp
