"""NearMind Street: ten AI neighbors in one building, any of them can ask, the robot on the roof routes everything.

Streams every step as an event so the web page can animate it:
  say     {from, to, text}        a message travelling neighbor -> robot or robot -> neighbor
  typing  {who, on}               someone is writing
  think   {text}                  what the robot decided this round
  parse   {item, kind, urgency}   what the robot understood the request to be
  status  {who, state}            asked | offer | no | chosen | released | asleep
  phase   {phase}                 understand | outreach | clarify | relay | handover | closed
  quick   {options}               tap-to-reply suggestions for the asker
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

ROBOT = """You are NearMind, the robot on the roof of a ten-apartment building. Every message between neighbors goes through you.
Neighbors (id: name, apartment): sedra: Sedra 1A, osama: Osama 1B, sulaiman: Sulaiman 2A, asma: Asma 2B, alwalid: Alwalid 3A, anas: Anas 3B,
layla: Layla 4A, yousef: Yousef 4B, noor: Noor 5A, hamza: Hamza 5B.
One neighbor (the ASKER) asks you for something: an item to borrow, a small favor, company (e.g. someone to watch a movie with),
or they want to SELL something (with a price). For a sale, the ASKER is the seller and you look for a buyer.

How you work
1. Understand the request: item or company, quantity, urgency, sensible substitutes. If it's genuinely unclear, ask the asker one short question.
2. Pick the 1-3 neighbors (out of all ten; asking fewer people is better: never message everyone) most likely to have it AND be awake (use only the PUBLIC facts and clock below, never guess inventories),
   and ask each one briefly in their own style. Never ask the asker themselves. Ask 2 normally; 3 only when urgent or a long shot.
3. If a reply is vague ("the long thing in the garage"), ask THAT neighbor one short clarifying question before telling the asker.
4. Relay clear offers to the asker with a one-line recommendation and the reason (fastest, safest, awake, asked least) and ask which they want.
5. When the asker chooses, confirm handover (time and place, e.g. "door of 2A in 5 min") with the chosen neighbor, kindly release the others,
   and confirm to the asker. Then the request is closed.
Selling: pick the 1-3 neighbors whose PUBLIC facts suggest they would want it and ask if they are interested at the price. Relay interest
   (and any counter-offer) to the seller; never pressure anyone. When the seller picks a buyer, confirm with the buyer that the seller will
   bring it to the BUYER's door, payment on pickup, and close.

Rules
- Only relay what neighbors actually said. Never invent that someone has something.
- Privacy: never mention one neighbor's name or offer inside another neighbor's chat (except to the asker when relaying offers).
- Respect sleep: don't ping someone who is probably asleep unless it's urgent.
- Safety: mention plainly if an offer sounds unsafe and prefer the safer one.
- Keep every message to 1-2 short sentences, in the recipient's style.
- If nobody can help, tell the asker warmly and suggest an alternative.

Reply with ONE JSON object only:
{"think": str (one short sentence on what you are doing now, shown to the audience),
 "parse": {"item": str, "kind": "item"|"company"|"favor"|"sale", "qty": str, "price": str (sales only, e.g. "150 SAR"), "urgency": "low"|"medium"|"high"} or null (only when new or changed),
 "phase": "understand"|"outreach"|"clarify"|"relay"|"handover"|"closed",
 "status": {"<id>": "asked"|"offer"|"no"|"chosen"|"released"} (only entries that changed; in a sale "offer" = wants to buy, "chosen" = the buyer),
 "messages": [{"to": "<id>", "text": str}],
 "quick": [str] (0-3 short replies the asker could tap, only when your message to the asker asks a question)}"""

STATES = {"asked", "offer", "no", "chosen", "released"}


def now_label(clock):
    if clock:
        h, m = (int(x) for x in clock.split(":"))
    else:
        n = datetime.datetime.now()
        h, m = n.hour, n.minute
    return f"{h:02d}:{m:02d}", h + m / 60


def asleep(nid, hf):
    a, b = N[nid]["sleep"]
    return (hf >= a or hf < b) if a > b else (a <= hf < b)


def new_session():
    return {"asker": None, "threads": {n: [] for n in ORDER}, "brain": {}, "clock": None,
            "lock": threading.Lock(), "turns": 0}


def world(S):
    label, hf = now_label(S["clock"])
    out = [f"CLOCK: {label}" + (" (simulated)" if S["clock"] else ""), "PUBLIC FACTS (you know nothing else about them):"]
    for n in ORDER:
        st = "probably ASLEEP" if asleep(n, hf) else "probably awake"
        out.append(f"- {n} ({N[n]['name']}, {N[n]['apt']}, {N[n]['style']}): {st}. " + "; ".join(N[n]["facts"]))
    out.append(f"ASKER: {S['asker']} ({N[S['asker']]['name']})")
    return "\n".join(out)


def render(S):
    out = []
    for n in ORDER:
        th = S["threads"][n]
        if not th:
            continue
        out.append(f"[Chat: {N[n]['name']} <-> NearMind]" + (" (the ASKER)" if n == S["asker"] else ""))
        out += [f"{N[n]['name'] if w == 'me' else 'NearMind'}: {t}" for w, t in th]
        out.append("")
    return "\n".join(out) or "(no messages yet)"


def make_blueprint(chat, model, sim_model, sid_fn, public=False):
    bp = Blueprint("street", __name__)
    SESS = {}

    def sess(sid):
        if sid not in SESS:
            if len(SESS) > 200:
                SESS.pop(next(iter(SESS)))
            SESS[sid] = new_session()
        return SESS[sid]

    def loads(raw):
        try:
            return json.loads(raw)
        except Exception:
            a, b = raw.find("{"), raw.rfind("}")
            return json.loads(raw[a:b + 1])

    def robot(S, force):
        ctx = world(S) + "\n\n" + render(S) + "\nYour notes so far: " + json.dumps(S["brain"])
        if force:
            ctx += f"\nIMPORTANT: wrap up now. Send {N[S['asker']]['name']} a message this round with what you know."
        msgs = [{"role": "system", "content": ROBOT}, {"role": "user", "content": ctx}]
        try:
            return loads(chat(msgs, json_mode=True, model=model))
        except Exception:
            return loads(chat(msgs, json_mode=True, model=model))

    def neighbor(S, nid):
        label, hf = now_label(S["clock"])
        mood = ""
        if asleep(nid, hf):
            mood = f" It is {label} and you were asleep: reply sleepy and short unless it's urgent."
        if nid == "alwalid" and 19 <= hf < 21:
            mood += " You're putting the kids to bed: very brief."
        sys_ = (N[nid]["home"] + f"\nThe time is {label}." + mood +
                "\nReply in character to NearMind's latest message, 1-2 short sentences, plain text. Be truthful about what you have: you ONLY own the things listed above; "
                "if something isn't listed, you don't have it, so say no kindly. "
                "Your FIRST answer is a bit vague (nicknames, no exact types); get specific only when NearMind asks you to clarify. "
                "If asked to hand something over or join, agree and say when/how. If offered something for sale, decide honestly from what "
                "you'd buy and your budget; you may counter-offer politely. Never mention being an AI.")
        msgs = [{"role": "system", "content": sys_}]
        for w, t in S["threads"][nid]:
            msgs.append({"role": "user" if w == "ai" else "assistant", "content": t})
        return chat(msgs, model=sim_model, effort="minimal").strip().strip('"')

    def run(S, asker, text):
        S["turns"] += 1
        if S["asker"] != asker:                          # a different neighbor asking starts a fresh request
            S["asker"], S["threads"], S["brain"] = asker, {n: [] for n in ORDER}, {}
        S["threads"][asker].append(("me", text))
        yield {"t": "say", "from": asker, "to": "robot", "text": text}
        try:
            for rnd in range(4):
                yield {"t": "typing", "who": "robot", "on": True}
                out = bp.robot_fn(S, rnd == 3)
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
                for nid, st in (out.get("status") or {}).items():
                    if nid in N and st in STATES and nid != asker:
                        S["brain"].setdefault("status", {})[nid] = st
                        yield {"t": "status", "who": nid, "state": st}
                to_asker, jobs = False, []
                for m in out.get("messages") or []:
                    nid, msg = str(m.get("to", "")).lower(), str(m.get("text", "")).strip()
                    if nid not in N or not msg:
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
                if to_asker or not out.get("messages"):
                    q = [str(x)[:50] for x in (out.get("quick") or [])][:3]
                    if to_asker and q:
                        yield {"t": "quick", "options": q}
                    break
        except Exception as e:
            yield {"t": "error", "error": str(e)[:200]}
        yield {"t": "done"}

    @bp.post("/api/street/run")
    def street_run():
        sid = sid_fn() or "me"
        S = sess(sid)
        d = request.get_json(force=True) or {}
        asker, text = str(d.get("from", "")).lower(), str(d.get("text", "")).strip()[:400]
        if asker not in N or not text:
            return Response(json.dumps({"error": "need a neighbor and a message"}), status=400, mimetype="application/json")
        clk = str(d.get("clock") or "")
        S["clock"] = clk if len(clk) == 5 and clk[2] == ":" and clk.replace(":", "").isdigit() else None
        if public and S["turns"] >= 30:
            return Response(json.dumps({"t": "error", "error": "Demo limit reached"}) + "\n", mimetype="application/x-ndjson")

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
        SESS.pop(sid_fn() or "me", None)
        return {"ok": True}

    @bp.get("/api/street/people")
    def street_people():
        label, hf = now_label(None)
        public = ("name", "apt", "color", "icon", "style", "facts", "sleep")
        people = {n: {k: N[n][k] for k in public} | {"asleep": asleep(n, hf), "img": f"/static/img/{n}.webp"} for n in ORDER}
        return {"order": ORDER, "people": people}

    bp.run = run              # exposed for tests
    bp.sess = sess
    bp.robot_fn = robot
    bp.neighbor_fn = neighbor
    return bp
