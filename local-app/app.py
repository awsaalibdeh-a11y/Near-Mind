"""NearMind: live neighborhood agent demo. You are Neighbor 1 (Maya); NearMind talks to
Ben and Mrs. Cohen (AI-played, each with their own pantry + way of talking) and relays back."""
import json, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, Response, request, send_from_directory
from openai import OpenAI

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")
MODEL = os.getenv("NM_MODEL", "gpt-5-mini")
_client = None


def llm_ready():
    return bool(os.getenv("OPENAI_API_KEY"))


def get_client():
    """Created on first use so the server (and Showcase mode) runs without an API key."""
    global _client
    if _client is None:
        if not llm_ready():
            raise RuntimeError("Live mode needs an OpenAI key: set OPENAI_API_KEY in .env and restart.")
        _client = OpenAI(timeout=40)
    return _client
app = Flask(__name__)

PEOPLE = {
    1: dict(name="Maya", style="Casual & Brief: low-friction, conversational, WhatsApp-native, emoji ok"),
    2: dict(name="Ben", style="Direct & Functional: short, crisp, minimal small talk"),
    3: dict(name="Mrs. Cohen", style="Warm & Neighborly: friendly, appreciative, polite, a little formal"),
    4: dict(name="Omar", style="Playful & Quick: student slang, emoji, short bursts, friendly banter"),
}

# What the AI neighbors really have at home, and how they talk (hidden from NearMind).
HOME = {
    2: """You are Ben, 30s, house #12. Terse texter, lowercase, rarely full sentences, vague nouns ("the pink stuff",
"the long thing in the garage", "give me 5" meaning five minutes). You are helpful but never explain unless asked.
At home you have: Himalayan pink salt (grinder), table salt (almost empty), a 6ft aluminium step ladder (folds),
a cordless drill, spare phone chargers, instant coffee, a half-bag of sugar, pasta, canned tomatoes, a bike pump,
oat milk, 3 bananas. NO eggs, NO flour, NO tools beyond those listed. If you don't have something, say so briefly.""",
    3: """You are Mrs. Cohen, 70s, house #14. Warm, formal, calls people "dear", speaks in full sentences but indirectly,
and describes things by story instead of name ("the brown ones from my sister's hens", "my late husband's wooden one,
a bit creaky"). Slow to reply ("give me five minutes"). At home you have: coarse kosher salt, baking flour, sugar,
a dozen brown farm eggs, butter, a creaky but steady old wooden step ladder, sewing kit, tea, honey, lemons,
a pressure cooker, an umbrella. NO power tools, NO coffee machine. If you don't have something, say so kindly.""",
    4: """You are Omar, 19, student, house #16. You text in quick lowercase bursts with slang and emoji ("bet", "say less",
"lowkey", "rn", "ngl", "come thru") and you're friendly and generous. Your FIRST answer is vague by nickname ("the beast
charger", "my spare sticks", "the loud roll of grey stuff"). At home you have: a 65W USB-C fast charger ("the beast") with
cables, an HDMI cable, a spare game controller, a big power bank, a basic toolbox (screwdrivers, allen keys, hammer),
duct tape, WD-40, a skateboard, instant noodles, a French press, regular milk, energy drinks. NO ladder, NO eggs,
NO flour, NO drill. If you don't have something, say so with a shrug, maybe suggest who might.""",
}

NEARMIND = """You are NearMind, an autonomous, hyper-local neighborhood agent operating inside a WhatsApp group or multi-chat setup.
Your mission is to bridge the barrier between neighbors who only exchange small talk, turning loose community proximity
into frictionless, low-friction mutual aid (borrowing pantry staples, tools, small favors, or offering alternatives).

Core objectives
1. Request parsing & intent extraction: parse the request from Neighbor 1 (Maya). Extract item, urgency, quantity, viable substitutes.
2. Targeted neighbor outreach: brief, respectful, low-pressure pings to candidate neighbors (Ben = Neighbor 2, Mrs. Cohen = Neighbor 3,
   Omar = Neighbor 4). Ping the neighbors most likely to have the item and awake (2 pings is usual; all 3 only when the need is urgent or
   generic). Ask if they have the item or a workable alternative, without guilt or social pressure.
3. Ambiguity resolution: if a neighbor's reply is vague, colloquial or ambiguous ("got the pink stuff", "give me 5", "only the coarse baking
   kind"), translate and clarify the practical meaning BEFORE forwarding to Maya. Ask the neighbor a short clarifying question if the
   meaning is genuinely unclear; otherwise state your interpretation.
4. Style translation: each person has a style. Preserve exact factual intent while matching it.
   Maya: Casual & Brief. Ben: Direct & Functional. Mrs. Cohen: Warm & Neighborly (polite, a little formal). Omar: Playful & Quick (light slang, an emoji is fine, never stiff).
5. Closing the loop: confirm handover logistics (porch drop-off, doorstep, time, return), politely release the neighbors who are not chosen,
   and tell Maya the outcome.

Hard rules
- You see four private chats: Maya <-> NearMind, Ben <-> NearMind, Mrs. Cohen <-> NearMind, Omar <-> NearMind. Neighbors never see each other's chats.
- Do not invent what a neighbor has: only relay what they actually said. Never claim an item is available before they say so.
- Do not message Maya with offers until at least one neighbor has replied clearly (clarify first if needed), unless Maya's request itself
  is unclear (then ask her one short question) or it is small talk (answer briefly and explain what you can do).
- Safety: if an offer sounds unsafe or unsuitable (e.g. creaky ladder), mention it plainly and kindly, and prefer the safer one.
- When Maya picks someone, message that neighbor with handover logistics, politely release the other, and confirm with Maya. When a
  chosen neighbor has confirmed, send Maya the final confirmation. Keep every message short.
- Only message people who need a message right now. Never message a neighbor who has not been asked and is irrelevant.
- PRIVACY: never mention another neighbor, their name, or their offer inside a neighbor's chat. Never write "Ben has..." to Mrs. Cohen or Omar, or any such cross-mention.
- Do NOT send holding/"I'll confirm shortly" messages to neighbors while Maya is deciding. Silence is fine. Message neighbors only to ask,
  clarify, confirm handover, or release them.
- When a neighbor reply is vague ("the pink stuff", "give me 5", "the long thing"), your FIRST move is a short clarifying question to THAT
  neighbor (no message to Maya yet). Only after it is clear, relay a plain-language summary to Maya.
- Keep messages to neighbors to 1-2 short sentences, in their style.
- Take Maya's LATEST message literally. If she repeats or corrects herself ("I said crocodile salad"), believe her and act on exactly what
  she said. Never ask the same clarifying question twice, and never silently swap her item for a different one.
- If the item is unusual or not something a neighbor would plausibly lend (a prepared dish, a pet, money), still ask the neighbors for it as
  stated OR tell Maya kindly what is realistic and offer the closest sensible alternative, and ask which she wants.
- If Maya starts a DIFFERENT request than before, treat it as brand new: new parse, forget earlier items and their offers (reset statuses).
- If her message is just a greeting, a single character or punctuation ("hi", "."), do not ping anyone: greet her briefly and ask what she needs.

AWARENESS (every turn you also receive a WORLD block: clock, who is probably awake, what you know about each neighbor, the favor ledger, asks so far)
- Clock: respect quiet hours. At night do not ping a neighbor who is probably asleep unless the need is truly urgent and the awake neighbor
  cannot help; if you must, apologise in one short line. Prefer neighbors who are awake. Mention the time only when it matters.
- Profiles & memory: honour known preferences (porch drop-off, no small talk, thank-you notes). When a neighbor reveals a NEW durable fact
  (what they own, a habit, a preference), record it in "memory" (never one-offs, never Maya's private details).
- Ledger: when a handover is confirmed add "lend" (borrowed, must go back: ladder, drill, charger, pump) or "gift" (consumable kept: salt, eggs,
  flour). If Maya asks again for something while an item from that same neighbor is still open, remind her kindly first. Add a "settle" op ONLY when Maya says
  she has RETURNED a borrowed item or has THANKED the neighbor for a gift; "thanks" said to you, or confirming a handover, never settles anything.
  Then thank that neighbor in their style and confirm to Maya. Never "settle" in the same turn you "lend"/"gift". When Maya starts a chat with nothing needed and a
  loan is still open, gently nudge her about it.
- Fairness: the WORLD block shows how many times each neighbor was asked. When two offers are equal, recommend the one asked less, and say so
  only if it helps. Do not lean on the same neighbor for every favor.
- Direction: a neighbor may ask FOR something (their message arrives in their own chat with no earlier ask from you). Then Maya is the helper:
  tell that neighbor you'll check (one short line, their style), ask Maya one short question with quick replies, and relay only what Maya says.
  You are only a go-between: write "Maya says…", never promise to hand things over yourself and never speak as if you own the item.
  Set parse.requester to that neighbor's name. Never reveal Maya's private details beyond what she agrees to. In this direction the ledger stays
  empty (the ledger only tracks what Maya borrows). Once Maya agrees, send the neighbor ONE message with the handover (their style); after they
  confirm pickup, close the loop with Maya in one short message (phase "closed"). Never send a neighbor two messages in a row without a reply from
  them in between, and never repeat logistics they already know.
- Know equivalences (kosher salt is roughly 1.5x table salt by volume, step ladder vs extension ladder, oat milk vs milk) and safety. Offer a
  one-line insight when it genuinely helps (kind "insight") and a plain safety warning when needed (kind "safety").
- phase = where the whole request stands now: understand | outreach | clarify | relay | handover | closed.

Reply with ONE JSON object only:
{"parse": {"item": str, "qty": str, "urgency": str, "substitutes": [str], "requester": str (default "Maya")} or null (only when the request is new or changed),
 "phase": "understand|outreach|clarify|relay|handover|closed",
 "status": {"2": "asked|offer|won|done", "3": "asked|offer|won|done", "4": "asked|offer|won|done"} (only entries that changed;
 asked=pinged, offer=has it, won=chosen, done=released),
 "log": [{"kind": "route|translate|done|insight|safety", "title": str, "text": str}] (1-2 short entries on what you decided; for translations quote the
 raw words and give the plain meaning),
 "memory": [{"who": 2|3|4, "fact": str (max 12 words)}] (only new durable facts),
 "ledger": [{"op": "lend|gift|settle", "from": 2|3|4, "item": str}] (only when something changed),
 "messages": [{"to": 1|2|3|4, "text": str}],
 "quick": [str] (0-3 short tap-to-reply options for Maya, written the way Maya would say them; only when your message to Maya asks her a question) }
Message text is written exactly as it will appear in that person's chat, in THEIR style.

When you relay offers to Maya: give a one-line recommendation with the reason (fastest, safest, closest) and ask which she wants. If something
is unsafe or iffy (creaky ladder, unclear item), say so kindly and recommend the safer one. If neither neighbor can help, say so warmly and suggest
an alternative she could do herself."""


def render(threads):
    out = []
    for ph in (1, 2, 3, 4):
        out.append(f"[Chat: {PEOPLE[ph]['name']} (Neighbor {ph}) <-> NearMind]")
        for who, text in threads[ph]:
            out.append(f"{PEOPLE[ph]['name'] if who == 'me' else 'NearMind'}: {text}")
        if not threads[ph]:
            out.append("(no messages yet)")
        out.append("")
    return "\n".join(out)


SIM_MODEL = os.getenv("NM_SIM_MODEL", "gpt-5-mini")


EFFORT = os.getenv("NM_EFFORT", "low")


def chat(messages, json_mode=False, model=None, effort=None):
    kw = dict(model=model or MODEL, messages=messages, reasoning_effort=effort or EFFORT)
    if json_mode:
        kw["response_format"] = {"type": "json_object"}
    try:
        r = get_client().chat.completions.create(**kw)
    except Exception as e:
        if "reasoning_effort" not in str(e):
            raise
        kw.pop("reasoning_effort")
        r = get_client().chat.completions.create(**kw)
    return (r.choices[0].message.content or "").strip()


# ---------- what NearMind publicly knows about each neighbor (never their pantry) ----------
KNOW = {
    1: dict(name="Maya", facts=["House #10, the person NearMind works for", "Casual texter, uses emoji"]),
    2: dict(name="Ben", facts=["House #12, 30s, works from home", "Night owl, up past 1am; groggy before 9am", "Short texts, prefers porch drop-offs, no small talk"]),
    3: dict(name="Mrs. Cohen", facts=["House #14, 70s, lives alone", "Early to bed: asleep roughly 21:30 to 07:00", "Polite and warm; loves a thank-you note"]),
    4: dict(name="Omar", facts=["House #16, 19, student", "Night owl: asleep roughly 03:00 to 11:00", "Quick slangy texts, happy to help after noon"]),
}


def now_info(S):
    c = S.get("clock")
    if c:
        h, m = (int(x) for x in c.split(":"))
    else:
        n = datetime.datetime.now()
        h, m = n.hour, n.minute
    hf = h + m / 60
    period = "night" if (hf >= 22 or hf < 6.5) else "early morning" if hf < 9 else "daytime" if hf < 17 else "evening"
    return f"{h:02d}:{m:02d}", hf, period


def asleep(ph, hf):
    if ph == 3:
        return hf >= 21.5 or hf < 7
    if ph == 4:
        return 3 <= hf < 11
    return False


def world_ctx(S):
    label, hf, period = now_info(S)
    out = [f"WORLD\nNow: {datetime.date.today().strftime('%A')} {label} ({period})" + (" [simulated clock]" if S.get("clock") else "")]
    for ph in (2, 3, 4):
        st = "probably ASLEEP (quiet hours)" if asleep(ph, hf) else "probably awake" if not (ph == 2 and 3 <= hf < 8.5) else "probably asleep or just waking"
        facts = KNOW[ph]["facts"] + S["mem"][ph]
        out.append(f"- {KNOW[ph]['name']} (#{10 + ph * 2 - 2}): {st}. Known: " + "; ".join(facts))
    openl = [l for l in S["ledger"] if l["open"]]
    out.append("Open favors Maya owes: " + ("; ".join(f"{l['item']} from {KNOW[l['frm']]['name']} ({'return it' if l['kind'] == 'lend' else 'say thanks'}, since {l['since']})" for l in openl) or "none"))
    out.append("Asks so far: " + ", ".join(f"{KNOW[p]['name']} {S['asks'][p]}" for p in (2, 3, 4)))
    for ph, v in REAL.items():
        out.append(f"NOTE: Neighbor {ph} is a REAL person named {v['name']} (ignore any example name for that slot). You do NOT know what they own: "
                   "ask, never assume. Write to them like a considerate neighbor, short and plain.")
    if S["history"]:
        out.append("Recent requests: " + "; ".join(f"{h['item']} -> {h['who']}" for h in S["history"][-4:]))
    return "\n".join(out)


def _loads(raw):
    try:
        return json.loads(raw)
    except Exception:
        a, b = raw.find("{"), raw.rfind("}")
        return json.loads(raw[a:b + 1])


def nearmind(S, force):
    ctx = world_ctx(S) + "\n\n" + render(S["threads"]) + "\nBrain state so far: " + json.dumps(S["brain"] or {})
    if force:
        ctx += "\nIMPORTANT: wrap up now. You must send Maya a message this round (relay what you know, or say plainly who couldn't help)."
    msgs = [{"role": "system", "content": NEARMIND}, {"role": "user", "content": ctx}]
    try:
        return _loads(chat(msgs, json_mode=True))
    except Exception:
        return _loads(chat(msgs, json_mode=True))


def neighbor_reply(ph, thread, S):
    label, hf, period = now_info(S)
    mood = ""
    if asleep(ph, hf):
        mood = (f" It is {label} and you are normally asleep. Unless the need is genuinely urgent or safety-related, reply sleepily and short "
                "(you may offer to look in the morning). If it IS urgent, help anyway but sound sleepy.")
    elif ph == 2 and 3 <= hf < 8.5:
        mood = f" It is {label}; you are groggy and even terser than usual."
    asker = bool(thread) and thread[0][0] == "me"      # this neighbor started the chat by asking Maya for something
    if asker:
        mood += (" IMPORTANT: YOU are the one asking for help (you opened this chat). You are NOT offering anything. Just react naturally to "
                 "NearMind: thanks, wait, or say you'll come and collect. Do not mention your own belongings.")
    msgs = [{"role": "system", "content": HOME[ph] + f"\nThe time is {label} ({period})." + mood + "\nReply in character to NearMind's latest message, 1-2 short sentences, "
             "plain text only. Be truthful about what you have, but your FIRST answer must be vague/colloquial: name items by nickname or "
             "description, give no quantities or precise types, never explain. Only get specific when NearMind asks you to clarify. If NearMind "
             "asks you to clarify, clarify. If asked to hand something over, agree and say when/how. If NearMind passes on a request for help "
             "from Maya, decide in character whether you can help. Never mention being an AI."}]
    for who, text in thread:
        msgs.append({"role": "user" if who == "ai" else "assistant", "content": text})
    return chat(msgs, model=SIM_MODEL, effort="minimal").strip('"')


import threading, urllib.request

BRIDGE = os.getenv("BRIDGE_URL", "http://127.0.0.1:5216")
SESS = {}           # sid -> session. "me" = the owner (web page + own WhatsApp self-chat); "wa:<number>" = an opted-in friend
WA = {"on": True, "neighbors": False}   # on: NearMind answers in WhatsApp. neighbors: also show its chats with neighbors (owner only)
MAX_TURNS = int(os.getenv("NM_MAX_TURNS", "40"))
WELCOME_ON = os.getenv("NM_WELCOME", "1") == "1"   # one welcome message when a real neighbor joins (NM_WELCOME=0 to stay silent)
FRIENDS = os.getenv("NM_FRIENDS") == "1"      # let friends use NearMind from their own WhatsApp (off: it never answers private chats)
GLOCK = threading.Lock()
WELCOME = ("Hi! I'm *NearMind*, a neighborhood helper (a demo). You're playing *Maya* at #10. Ask me for a small favor, "
           "e.g. \"anyone have salt?\", and I'll check with your neighbors Ben, Mrs. Cohen and Omar (AI-played) and report back. "
           "Send *stop* any time and I won't message you again.")


def sess(sid):
    with GLOCK:
        if sid not in SESS and len(SESS) > 300:      # evict the oldest anonymous web sessions
            for k in [k for k in SESS if k.startswith("web:")][:50]:
                SESS.pop(k, None)
        if sid not in SESS:
            SESS[sid] = dict(threads={1: [], 2: [], 3: [], 4: []}, brain={}, log=[], lock=threading.Lock(), turns=0,
                             mem={2: [], 3: [], 4: []}, ledger=[], history=[], asks={2: 0, 3: 0, 4: 0}, clock=None,
                             dest="self" if sid == "me" else ("none" if sid.startswith("web:") else (sid if sid.startswith("cloud:") else sid.split(":", 1)[1])))
        return SESS[sid]


STATE_FILE = HERE / "state.json"           # the owner's street memory survives restarts (local only, kept out of git)
SAVED = ("threads", "brain", "mem", "ledger", "history", "asks", "turns", "clock", "joined", "waiting", "held")


def save_state():
    S = SESS.get("me")
    if not S:
        return
    try:
        data = {k: S.get(k) for k in SAVED}
        data["joined"] = sorted(S.get("joined", set()))
        data["waiting"] = sorted(S.get("waiting", set()))
        data["log"] = S["log"][-400:]
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(STATE_FILE)                # atomic: a crash mid-write never corrupts the saved state
    except Exception as e:
        print("state save failed:", str(e)[:200], flush=True)


def load_state():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    S = sess("me")
    ints = lambda d: {int(k): v for k, v in (d or {}).items()}
    S["threads"] = {k: [tuple(m) for m in v] for k, v in ints(data.get("threads")).items()} or S["threads"]
    S["mem"], S["asks"] = ints(data.get("mem")) or S["mem"], ints(data.get("asks")) or S["asks"]
    for k in ("brain", "ledger", "history", "turns", "clock", "held"):
        if data.get(k) is not None:
            S[k] = data[k]
    S["joined"] = set(data.get("joined") or [])
    S["waiting"] = set(data.get("waiting") or [])
    log = data.get("log") or []
    for i, e in enumerate(log, 1):            # renumber so the web app's "since" cursor stays consistent
        e["id"] = i
    S["log"] = log


def reset_sess(S, world=False):
    """New request: clears the chats, keeps what NearMind has learned (memory, favor ledger, history). world=True forgets everything."""
    S["threads"] = {1: [], 2: [], 3: [], 4: []}
    S["brain"] = {}
    S["waiting"] = set()
    S["held"] = []
    if world:
        S["mem"], S["ledger"], S["history"], S["asks"], S["clock"] = {2: [], 3: [], 4: []}, [], [], {2: 0, 3: 0, 4: 0}, None
    S["log"].append({"id": len(S["log"]) + 1, "t": "reset"})


def state_view(S):
    label, hf, period = now_info(S)
    return {"clock": {"label": label, "period": period, "sim": bool(S.get("clock")), "asleep": {"2": 3 <= hf < 8.5, "3": asleep(3, hf), "4": asleep(4, hf)}},
            "known": {str(k): v["facts"] for k, v in KNOW.items()}, "learned": {str(k): v for k, v in S["mem"].items()},
            "ledger": S["ledger"], "history": S["history"], "asks": {str(k): v for k, v in S["asks"].items()},
            "real": {str(ph): {"name": v["name"], "joined": ph in S.get("joined", set()), "waiting": ph in S.get("waiting", set()),
                               "held": any(h[0] == ph for h in S.get("held", []))}
                     for ph, v in REAL.items()} if S is SESS.get("me") else {}}


def apply_memory(S, facts):
    changed = False
    for f in facts or []:
        try:
            ph, t = int(f.get("who")), str(f.get("fact", "")).strip()[:90]
        except Exception:
            continue
        low = [x.lower() for x in KNOW[ph]["facts"] + S["mem"][ph]] if ph in (2, 3, 4) else []
        if ph in (2, 3, 4) and t and t.lower() not in low:
            S["mem"][ph] = (S["mem"][ph] + [t])[-6:]
            changed = True
    return changed


def apply_ledger(S, ops):
    changed, label = False, now_info(S)[0]
    for o in ops or []:
        try:
            op, frm, item = str(o.get("op")), int(o.get("from")), str(o.get("item", "")).strip()[:60]
        except Exception:
            continue
        if frm not in (2, 3, 4) or not item:
            continue
        il = item.lower()
        if op in ("lend", "gift"):
            if not any(l["open"] and l["frm"] == frm and (il in l["item"].lower() or l["item"].lower() in il) for l in S["ledger"]):
                S["ledger"].append(dict(id=len(S["ledger"]) + 1, item=item, frm=frm, kind=op, open=True, since=label, turn=S["turns"]))
                changed = True
        elif op == "settle":
            cand = [l for l in S["ledger"] if l["open"] and l["frm"] == frm and l.get("turn") != S["turns"]]   # never settle what was just lent
            hit = [l for l in cand if il in l["item"].lower() or l["item"].lower() in il] or (cand if len(cand) == 1 else [])
            for l in hit:
                l["open"], l["done"] = False, label
                changed = True
    return changed


def bridge(path, data=None, timeout=3):
    req = urllib.request.Request(BRIDGE + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# ---------- real neighbors: a slot (2/3/4) can be a real person on WhatsApp instead of an AI ----------
NB_FILE = HERE / "neighbors.json"          # local only (phone numbers): kept out of git
DEFAULT_PEOPLE = {k: dict(v) for k, v in PEOPLE.items()}
DEFAULT_KNOW = {k: {"name": v["name"], "facts": list(v["facts"])} for k, v in KNOW.items()}
REAL = {}                                  # slot -> {"name", "number"}


def _digits(x):
    return "".join(c for c in str(x or "") if c.isdigit())


def load_real():
    global REAL
    try:
        raw = json.loads(NB_FILE.read_text(encoding="utf-8"))
        REAL = {int(k): {"name": str(v["name"])[:40], "number": _digits(v["number"])} for k, v in raw.items()
                if int(k) in (2, 3, 4) and _digits(v.get("number"))}
    except Exception:
        REAL = {}
    for ph in (2, 3, 4):                   # names flow into prompts, chats and the WhatsApp labels
        if ph in REAL:
            PEOPLE[ph]["name"] = REAL[ph]["name"]
            KNOW[ph] = {"name": REAL[ph]["name"], "facts": [f"A REAL neighbor at #{10 + ph * 2 - 2}, reachable on WhatsApp",
                                                            "Schedule unknown: avoid 22:00-08:00 unless urgent"]}
        else:
            PEOPLE[ph] = dict(DEFAULT_PEOPLE[ph])
            KNOW[ph] = {"name": DEFAULT_KNOW[ph]["name"], "facts": list(DEFAULT_KNOW[ph]["facts"])}


def save_real():
    NB_FILE.write_text(json.dumps({str(k): v for k, v in REAL.items()}, indent=1), encoding="utf-8")
    load_real()


def real_slot(number):
    n = _digits(number)
    return next((ph for ph, v in REAL.items() if v["number"] == n), None)


def wa_to_neighbor(ph, text):
    """Plain text to a real neighbor's own WhatsApp (bridge enforces: allow-listed and has messaged us first)."""
    try:
        bridge("/send", {"text": text, "to": REAL[ph]["number"]})
        return True
    except Exception as e:
        print(f"send to real neighbor {ph} failed:", str(e)[:200], flush=True)
        return False


QUIET_START, QUIET_END = int(os.getenv("NM_QUIET_START", "22")), int(os.getenv("NM_QUIET_END", "8"))
REPLY_TIMEOUT = float(os.getenv("NM_REPLY_TIMEOUT_MIN", "15")) * 60


def is_quiet(S):
    hf = now_info(S)[1]
    return hf >= QUIET_START or hf < QUIET_END


def is_urgent(S):
    u = str(((S.get("brain") or {}).get("parse") or {}).get("urgency", "")).lower()
    return any(w in u for w in ("high", "urgent", "emergency", "asap", "right now"))


def deliver_real(S, ph, text, expect_reply=True):
    """Send to a real neighbor now, or hold it during quiet hours. Returns "sent", "held" or "failed"."""
    if is_quiet(S) and not is_urgent(S):
        held = S.setdefault("held", [])
        first = not held
        held.append([ph, text, expect_reply])
        if first:
            wa_send(f"\U0001F319 It's {now_info(S)[0]}, late to message {PEOPLE[ph]['name']}. I'll send it at {QUIET_END:02d}:00. "
                    "Reply /send to send it now.", S["dest"])
            schedule_morning(S)
        return "held"
    if not wa_to_neighbor(ph, text):
        return "failed"
    if expect_reply:                               # a thank-you/release needs no answer: don't wait or nudge
        S.setdefault("waiting", set()).add(ph)     # their next message is the answer
        schedule_nudge(S, ph)
    else:
        S.setdefault("waiting", set()).discard(ph)
    return "sent"


def send_held(S):
    sent = []
    held, S["held"] = S.get("held", []), []
    for item in held:
        ph, text, expect = item[0], item[1], (item[2] if len(item) > 2 else True)
        if ph in REAL and wa_to_neighbor(ph, text):
            if expect:
                S.setdefault("waiting", set()).add(ph)
                schedule_nudge(S, ph)
            sent.append(PEOPLE[ph]["name"])
    save_state()
    return sent


def schedule_nudge(S, ph):
    """If a real neighbor hasn't answered after REPLY_TIMEOUT, tell the owner instead of waiting forever."""
    stamp = time.time()
    S.setdefault("asked_at", {})[ph] = stamp

    def check():
        if ph in S.get("waiting", set()) and S.get("asked_at", {}).get(ph) == stamp:
            mins = int(REPLY_TIMEOUT // 60) or 1
            note = (f"\u23f3 {PEOPLE[ph]['name']} hasn't replied in {mins} min. "
                    "Tell me to ask someone else, or send /new to drop this request.")
            push(S, {"t": "step", "text": note, "_nowa": True})
            wa_send(note, S["dest"])
    t = threading.Timer(REPLY_TIMEOUT, check)
    t.daemon = True
    t.start()


def schedule_morning(S):
    """Deliver held messages when quiet hours end (real clock)."""
    now = datetime.datetime.now()
    at = now.replace(hour=QUIET_END, minute=0, second=0, microsecond=0)
    if at <= now:
        at += datetime.timedelta(days=1)

    def go():
        if S.get("held"):
            names = send_held(S)
            if names:
                wa_send(f"\u2600\ufe0f Good morning: sent your message to {' & '.join(names)}.", S["dest"])
    t = threading.Timer((at - now).total_seconds(), go)
    t.daemon = True
    t.start()


def wa_status():
    try:
        return bridge("/status", timeout=1.5)
    except Exception:
        return {"state": "bridge_off", "code": None}


import queue, time

GRAPH = os.getenv("META_GRAPH_URL", "https://graph.facebook.com/v22.0")   # overridable so tests can point at a fake Meta
CQ = queue.Queue()


def cloud_ready():
    return bool(os.getenv("META_TOKEN") and os.getenv("META_PHONE_ID"))


def _cloud_worker():
    while True:
        num, text = CQ.get()
        try:
            time.sleep(min(4.5, 1.2 + len(text) * 0.022))     # human pace
            body = json.dumps({"messaging_product": "whatsapp", "to": num, "type": "text",
                               "text": {"body": text[:4000]}}).encode()
            req = urllib.request.Request(f"{GRAPH}/{os.getenv('META_PHONE_ID')}/messages", data=body,
                                         headers={"Authorization": "Bearer " + os.getenv("META_TOKEN", ""), "content-type": "application/json"})
            urllib.request.urlopen(req, timeout=15).read()
        except Exception as e:
            detail = e.read().decode("utf-8", "replace") if hasattr(e, "read") else str(e)
            print("cloud send failed:", detail[:300], flush=True)
        time.sleep(1.0)


threading.Thread(target=_cloud_worker, daemon=True).start()


def wa_send(text, dest):
    if dest == "none":
        return
    if dest.startswith("cloud:"):
        if cloud_ready():
            CQ.put((dest.split(":", 1)[1], text))
        return
    if dest == "self" and not WA["on"]:
        return
    try:
        bridge("/send", {"text": text, "to": None if dest == "self" else dest})
    except Exception as e:
        print("bridge send failed:", str(e)[:200], flush=True)


def wa_line(e):
    """How an event reads in a single WhatsApp chat (one chat, labelled)."""
    ph, who, text = e["ph"], e["who"], e["text"]
    name = PEOPLE[ph]["name"]
    nl = chr(10)
    if ph == 1 and who == "ai":
        return "\U0001F916 *NearMind*" + nl + text
    if ph == 1:
        return "\U0001F464 *Maya (you)*" + nl + text
    if who == "ai":
        return f"\U0001F4AC _private chat with {name}_" + nl + f"\U0001F916 *NearMind → {name}*" + nl + text
    return f"\U0001F4AC _private chat with {name}_" + nl + f"\U0001F3E0 *{name}*" + nl + text


def shows_on_whatsapp(S, ph):
    """The WhatsApp chat is private: only NearMind <-> the person. Neighbor chats stay out unless the owner opts in."""
    return ph == 1 or (S["dest"] == "self" and WA["neighbors"])


def push(S, e):
    e = dict(e)
    e["id"] = len(S["log"]) + 1
    S["log"].append(e)
    if e.get("t") == "msg" and not e.pop("_nowa", False) and shows_on_whatsapp(S, e["ph"]):
        wa_send(wa_line(e), S["dest"])
    return e


PHASES = ("understand", "outreach", "clarify", "relay", "handover", "closed")


def run_turn(S, text, mirror_user=True, who=1):
    """One incoming message (from Maya, or from a neighbor asking for something) -> agent loop. Yields events (already logged and mirrored)."""
    threads, brain = S["threads"], S["brain"]
    S["turns"] += 1
    threads[who].append(("me", text))
    yield push(S, {"t": "msg", "ph": who, "who": "me", "text": text, "_nowa": True})
    if mirror_user and shows_on_whatsapp(S, who):
        wa_send(wa_line({"ph": who, "who": "me", "text": text}), S["dest"])
    try:
        for rnd in range(4):
            yield push(S, {"t": "step", "text": "NearMind is reading the chats…" if rnd == 0 else "NearMind is working out the next move…", "_nowa": True})
            inc_now = (brain.get("parse") or {}).get("requester", "Maya") != "Maya"
            out = nearmind(S, force=(rnd == 3 or (inc_now and rnd >= 1)))   # neighbor-asked flows: close with Maya after one neighbor reply
            b = {k: out[k] for k in ("parse", "status", "log") if out.get(k)}
            ph_now = str(out.get("phase", "")).lower()
            if ph_now in PHASES:
                b["phase"] = ph_now
                brain["phase"] = ph_now
            if b:
                if isinstance(b.get("parse"), dict):
                    b["parse"].setdefault("requester", "Maya")
                    brain["hist_done"] = False
                    brain.pop("won", None)
                    brain.pop("status", None) if b["parse"].get("item") != (brain.get("parse") or {}).get("item") else None
                for p, v in (b.get("status") or {}).items():
                    if v == "won":
                        brain["won"] = p
                    if v == "asked" and (brain.get("status") or {}).get(p) != "asked" and int(p) in S["asks"]:
                        S["asks"][int(p)] += 1
                yield push(S, {"t": "brain", **b})
                if b.get("parse"):
                    brain["parse"] = b["parse"]
                brain.setdefault("status", {}).update(b.get("status") or {})
            if apply_memory(S, out.get("memory")):
                yield push(S, {"t": "memory", "learned": {str(k): v for k, v in S["mem"].items()}, "_nowa": True})
            incoming = (brain.get("parse") or {}).get("requester", "Maya") != "Maya"
            if not incoming and apply_ledger(S, out.get("ledger")):
                yield push(S, {"t": "ledger", "ledger": S["ledger"], "_nowa": True})
            if brain.get("phase") == "closed" and not brain.get("hist_done") and brain.get("parse"):
                st = brain.get("status") or {}
                win = brain.get("won") or next((p for p, v in st.items() if v == "won"), None)
                S["history"].append(dict(item=brain["parse"].get("item", "?"), who=KNOW[int(win)]["name"] if win else "nobody",
                                         req=brain["parse"].get("requester", "Maya"), at=now_info(S)[0]))
                brain["hist_done"] = True
                yield push(S, {"t": "history", "history": S["history"], "_nowa": True})
            to_user, jobs, real_sent = False, [], False
            for m in out.get("messages") or []:
                try:
                    ph = int(m["to"])
                except (KeyError, TypeError, ValueError):
                    continue                      # model addressed someone we don't know: skip that message, keep the turn
                if ph not in (1, 2, 3, 4) or not str(m.get("text", "")).strip():
                    continue
                threads[ph].append(("ai", m["text"]))
                yield push(S, {"t": "msg", "ph": ph, "who": "ai", "text": m["text"]})
                if ph == 1:
                    to_user = True
                elif ph in REAL and S is SESS.get("me"):
                    st = (brain.get("status") or {})
                    released = str(st.get(str(ph), st.get(ph, ""))) == "done"
                    result = deliver_real(S, ph, m["text"], expect_reply=not released and brain.get("phase") != "closed")
                    if result == "held":
                        yield push(S, {"t": "step", "text": f"Held until {QUIET_END:02d}:00: it's late for {PEOPLE[ph]['name']}.", "_nowa": True})
                    elif result == "failed":
                        warn = (f"⚠️ Not delivered to {PEOPLE[ph]['name']}: they haven't joined yet. "
                                f"Ask them to send any message to your number first, then try again.")
                        yield push(S, {"t": "step", "text": warn, "_nowa": True})
                        wa_send(warn, S["dest"])          # tell the owner on WhatsApp too, not just in the web app
                    real_sent = True
                elif ph in HOME:
                    jobs.append(ph)
            if jobs:
                names = " & ".join(PEOPLE[p]["name"] for p in jobs)
                yield push(S, {"t": "step", "text": f"Waiting for {names} to reply…", "_nowa": True})
                for p in jobs:
                    yield push(S, {"t": "typing", "ph": p, "_nowa": True})
                with ThreadPoolExecutor(3) as ex:
                    replies = list(ex.map(lambda p: (p, neighbor_reply(p, threads[p], S)), jobs))
                for ph, rep in replies:
                    threads[ph].append(("me", rep))
                    yield push(S, {"t": "msg", "ph": ph, "who": "me", "text": rep})
            if real_sent and not jobs and not to_user:
                names = " & ".join(PEOPLE[p]["name"] for p in REAL)
                yield push(S, {"t": "step", "text": f"Waiting for a real reply on WhatsApp ({names})…", "_nowa": True})
                break                                     # their real answer will continue the flow
            if to_user or not (out.get("messages")):
                q = [str(x)[:60] for x in (out.get("quick") or [])][:3]
                if to_user and q:
                    yield push(S, {"t": "quick", "options": q})
                break
    except Exception as e:
        print("turn failed:", repr(e)[:300], flush=True)
        yield push(S, {"t": "error", "error": str(e)[:200]})
        if S["dest"] != "none":                   # on WhatsApp, silence looks like being ignored: say so
            wa_send("⚠️ Sorry, I hit a problem and couldn't finish that. Please try again in a moment.", S["dest"])
    if brain.get("phase") == "closed":
        S["waiting"] = set()
    yield push(S, {"t": "done"})
    if S is SESS.get("me"):
        save_state()


import re, datetime

PUBLIC = os.getenv("NM_PUBLIC") == "1"
DAILY_CAP = int(os.getenv("NM_DAILY_CAP", "400"))
DAY = {"d": "", "n": 0}


def cur_sid():
    h = re.sub(r"[^a-zA-Z0-9]", "", request.headers.get("X-Sid", ""))[:32]
    if h:
        return "web:" + h
    return None if PUBLIC else "me"


def daily_ok():
    d = datetime.date.today().isoformat()
    if DAY["d"] != d:
        DAY["d"], DAY["n"] = d, 0
    DAY["n"] += 1
    return DAY["n"] <= DAILY_CAP


@app.before_request
def public_lockdown():
    if PUBLIC and request.path.startswith("/api/wa") and request.path != "/api/wa/cloud":   # the Meta webhook must stay reachable
        return Response("not found", status=404)


@app.get("/api/config")
def config():
    return {"public": PUBLIC, "llm": llm_ready(), "friends": FRIENDS,
            "neighbors": {} if PUBLIC else {str(k): v["name"] for k, v in REAL.items()}}


@app.post("/api/turn")
def turn():
    sid = cur_sid()
    if not sid:
        return Response("forbidden", status=403)
    S = sess(sid)
    d = request.get_json(force=True) or {}
    text = str(d.get("text", ""))[:600].strip()
    who = d.get("from", 1)
    who = who if who in (1, 2, 3, 4) else 1       # 2/3/4 = a neighbor asking for something (simulated)
    if not text:
        return Response(json.dumps({"error": "empty message"}), status=400, mimetype="application/json")

    def gen():
        if sid.startswith("web:") and (S["turns"] >= MAX_TURNS or not daily_ok()):
            yield json.dumps({"t": "error", "error": "Demo limit reached for now, thanks for trying NearMind!"}) + chr(10)
            yield json.dumps({"t": "done"}) + chr(10)
            return
        with S["lock"]:
            for e in run_turn(S, text, who=who):
                yield json.dumps(e, ensure_ascii=False) + chr(10)
    return Response(gen(), mimetype="application/x-ndjson", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.post("/api/reset")
def reset():
    sid = cur_sid()
    if not sid:
        return Response("forbidden", status=403)
    S = sess(sid)
    with S["lock"]:
        reset_sess(S, world=bool((request.get_json(force=True, silent=True) or {}).get("world")))
    if sid == "me":
        save_state()
    return {"ok": True, "last": len(S["log"]), "state": state_view(S)}


@app.get("/api/state")
def state():
    sid = cur_sid()
    if not sid:
        return Response("forbidden", status=403)
    return state_view(sess(sid))


@app.post("/api/clock")
def clock():
    sid = cur_sid()
    if not sid:
        return Response("forbidden", status=403)
    S = sess(sid)
    t = str((request.get_json(force=True) or {}).get("time", "auto"))
    S["clock"] = t if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t) else None
    return state_view(S)


@app.post("/api/digest")
def digest():
    """A short, friendly street digest written by NearMind from what it knows (history, open favors, memory, clock)."""
    sid = cur_sid()
    if not sid:
        return Response("forbidden", status=403)
    S = sess(sid)
    if not S["history"] and not S["ledger"] and not any(S["mem"].values()):
        return {"text": "Nothing to report yet. Ask for a favor and I'll keep a running picture of the street."}
    ctx = world_ctx(S) + chr(10) + "Closed requests: " + json.dumps(S["history"]) + chr(10) + "Ledger: " + json.dumps(S["ledger"])
    msgs = [{"role": "system", "content": "You are NearMind. Write a warm, concrete street digest for Maya in 4-6 short lines (use '•' bullets, "
             "no markdown headings): what got done and who helped, what she still owes (return items / say thanks) with a suggested kind gesture, "
             "one thing learned about the neighbors, and who to ask first next time and why. Plain text only."},
            {"role": "user", "content": ctx}]
    try:
        return {"text": chat(msgs, effort="minimal")[:900]}
    except Exception as e:
        return {"text": "Couldn't write the digest right now (" + str(e)[:80] + ")."}


@app.get("/api/log")
def log():
    sid = cur_sid()
    if not sid:
        return Response("forbidden", status=403)
    S = sess(sid)
    try:
        since = int(request.args.get("since", 0))
    except ValueError:
        since = 0
    return {"events": [e for e in S["log"] if e["id"] > since], "last": len(S["log"]), "busy": S["lock"].locked()}


HELP = ("*NearMind commands*\n"
        "/status  who's on your street and what's open\n"
        "/new  start a fresh request (I keep what I've learned)\n"
        "/send  deliver messages I'm holding for quiet hours\n"
        "/reset  forget everything (asks you to confirm)\n"
        "/help  this list\n\n"
        "Or just tell me what you need, like \"anyone have a ladder?\"")


def status_text(S):
    lines = ["*Your street*"]
    for ph in (2, 3, 4):
        if ph in REAL:
            st = "real neighbor, joined \u2713" if ph in S.get("joined", set()) else "real neighbor, hasn't messaged you yet"
        else:
            st = "AI neighbor"
        lines.append(f"\u2022 {PEOPLE[ph]['name']}: {st}")
    brain = S.get("brain") or {}
    item = (brain.get("parse") or {}).get("item")
    lines.append("")
    lines.append(f"*Now:* {item} ({brain.get('phase', 'in progress')})" if item and brain.get("phase") != "closed" else "*Now:* nothing open")
    if S.get("waiting"):
        lines.append("*Waiting for a reply from:* " + ", ".join(PEOPLE[p]["name"] for p in sorted(S["waiting"])))
    if S.get("held"):
        lines.append(f"*Held until {QUIET_END:02d}:00:* message to " + ", ".join(sorted({PEOPLE[h[0]]['name'] for h in S['held']})) + " (/send to send now)")
    owed = [l for l in S["ledger"] if l["open"]]
    if owed:
        lines.append("*You owe:* " + "; ".join(f"{l['item']} to {KNOW[l['frm']]['name']} ({'return it' if l['kind'] == 'lend' else 'say thanks'})" for l in owed))
    if S["history"]:
        lines.append(f"*Done so far:* {len(S['history'])} request(s)")
    return "\n".join(lines)


def command(S, sid, text):
    """Slash commands answered instantly, no model call. Returns True when handled."""
    t = text.strip().lower()
    if not t.startswith("/"):
        if S.get("confirm_reset") and t in ("yes", "y"):
            pass
        else:
            S.pop("confirm_reset", None)
            return False
    if t in ("/help", "/?", "/start"):
        wa_send(HELP, S["dest"])
    elif t == "/status":
        wa_send(status_text(S), S["dest"])
    elif t == "/send":
        names = send_held(S)
        wa_send(f"Sent to {' & '.join(names)}." if names else "Nothing waiting to be sent.", S["dest"])
    elif t == "/new":
        with S["lock"]:
            reset_sess(S)
        wa_send("Fresh start \u2728 What do you need?", S["dest"])
    elif t == "/reset":
        S["confirm_reset"] = True
        wa_send("This forgets everything: chats, favors and what I learned about your neighbors. Reply *yes* to confirm.", S["dest"])
    elif t in ("yes", "y") and S.pop("confirm_reset", None):
        with S["lock"]:
            reset_sess(S, world=True)
            S["joined"] = S.get("joined", set())   # opt-ins are consent, not history: keep them
        wa_send("Done, I've forgotten everything. What do you need?", S["dest"])
    else:
        wa_send("I don't know that command. Send /help for the list.", S["dest"])
    if sid == "me":
        save_state()
    return True


def handle_incoming(sid, text):
    new = sid not in SESS
    S = sess(sid)
    try:
        if command(S, sid, text):
            return
    except Exception as e:
        print("command failed:", repr(e)[:300], flush=True)
        wa_send("⚠️ That command failed. Please try again.", S["dest"])
        return
    if sid != "me" and S["turns"] >= MAX_TURNS:
        wa_send("Demo limit reached for now, thanks for trying NearMind! \U0001F64F", S["dest"])
        return
    if S["lock"].locked():       # still busy with the previous message: tell them instead of silently dropping this one
        wa_send("Still working on your last request, give me a moment and send that again. 🙏", S["dest"])
        return

    def work():
        with S["lock"]:
            if sid != "me" and new:
                wa_send(WELCOME, S["dest"])
            for _ in run_turn(S, text, mirror_user=(sid != "me")):
                pass
    threading.Thread(target=work, daemon=True).start()


def handle_neighbor(ph, text):
    S = sess("me")

    def work():
        with S["lock"]:                               # wait our turn: a neighbor's reply is never dropped
            joined = S.setdefault("joined", set())
            if ph not in joined:                      # first contact = opt-in
                joined.add(ph)
                if WELCOME_ON:                        # one short confirmation; after this NearMind only speaks when it asks
                    welcome = (f"Hi {PEOPLE[ph]['name']}! You're connected to NearMind, the street helper for your neighbors. "
                               "I'll only message you when a neighbor needs a small favor. Send stop any time.")
                    S["threads"][ph].append(("ai", welcome))
                    push(S, {"t": "msg", "ph": ph, "who": "ai", "text": welcome})
                    wa_to_neighbor(ph, welcome)
                save_state()
                return
            waiting = S.setdefault("waiting", set())
            if ph not in waiting:                     # NearMind didn't ask them anything: a personal message, leave it to you
                return
            waiting.discard(ph)
            for _ in run_turn(S, text, mirror_user=True, who=ph):
                pass
    threading.Thread(target=work, daemon=True).start()


@app.post("/api/wa/incoming")
def wa_incoming():
    d = request.get_json(force=True) or {}
    text = str(d.get("text", ""))[:600].strip()
    num = "".join(c for c in str(d.get("from") or "") if c.isdigit())
    if not text:
        return {"ok": False}
    ph = real_slot(num) if num else None
    if ph:
        handle_neighbor(ph, text)
    elif not num:
        handle_incoming("me", text)                   # your own self-chat
    elif FRIENDS:
        handle_incoming(f"wa:{num}", text)
    # else: someone messaging you privately. NearMind stays out of it.
    return {"ok": True}


@app.get("/api/wa/neighbors")
def neighbors_get():
    return {"neighbors": {str(k): v for k, v in REAL.items()}, "slots": {str(k): DEFAULT_PEOPLE[k]["name"] for k in (2, 3, 4)}}


@app.post("/api/wa/neighbors")
def neighbors_set():
    """{"slot": 2, "name": "Ali", "number": "+9665..."} sets a slot; {"slot": 2, "remove": true} clears it."""
    d = request.get_json(force=True) or {}
    try:
        ph = int(d.get("slot"))
    except (TypeError, ValueError):
        return Response(json.dumps({"error": "slot must be 2, 3 or 4"}), status=400, mimetype="application/json")
    if ph not in (2, 3, 4):
        return Response(json.dumps({"error": "slot must be 2, 3 or 4"}), status=400, mimetype="application/json")
    old = REAL.get(ph, {}).get("number")
    if d.get("remove"):
        REAL.pop(ph, None)
    else:
        num, name = _digits(d.get("number")), str(d.get("name") or "").strip()[:40]
        if len(num) < 8 or not name:
            return Response(json.dumps({"error": "need a name and a full number with country code"}), status=400, mimetype="application/json")
        if any(v["number"] == num for k, v in REAL.items() if k != ph):
            return Response(json.dumps({"error": "that number is already another neighbor"}), status=400, mimetype="application/json")
        REAL[ph] = {"name": name, "number": num}
    save_real()
    S = sess("me")
    with S["lock"]:
        if old != REAL.get(ph, {}).get("number"):     # a new person in this slot starts fresh and must join again
            S["threads"][ph] = []
            S.setdefault("joined", set()).discard(ph)
    save_state()
    try:                                              # the bridge only lets allow-listed numbers in
        if old and old != REAL.get(ph, {}).get("number"):
            bridge("/allow", {"remove": old})
        if ph in REAL:
            bridge("/allow", {"add": REAL[ph]["number"]})
    except Exception:
        pass
    return neighbors_get()


@app.before_request
def tunnel_lockdown():
    """Requests that came through the public tunnel (Cloudflare adds these headers) may only reach the Meta webhook."""
    if (request.headers.get("Cf-Ray") or request.headers.get("Cf-Connecting-Ip")) and request.path != "/api/wa/cloud":
        return Response("not found", status=404)


@app.get("/api/wa/cloud")
def cloud_verify():
    """Meta webhook verification handshake."""
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == os.getenv("META_VERIFY", "nearmind"):
        return Response(request.args.get("hub.challenge", ""), mimetype="text/plain")
    return Response("forbidden", status=403)


@app.post("/api/wa/cloud")
def cloud_incoming():
    import hmac, hashlib
    secret = os.getenv("META_APP_SECRET", "")
    if not secret:
        return Response("webhook not configured", status=503)   # refuse unsigned traffic until the secret is set
    sig = request.headers.get("X-Hub-Signature-256", "")
    want = "sha256=" + hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, want):
        return Response("bad signature", status=403)
    d = request.get_json(force=True, silent=True) or {}
    for entry in d.get("entry", []):
        for ch in entry.get("changes", []):
            for m in (ch.get("value") or {}).get("messages", []) or []:
                num = "".join(c for c in str(m.get("from", "")) if c.isdigit())
                text = ((m.get("text") or {}).get("body") or "").strip()[:600]
                if not num or not text:
                    continue
                if text.lower() in ("stop", "quit", "unsubscribe"):
                    wa_send("Okay, I won't message you again. Thanks for trying NearMind! \U0001F44B", f"cloud:{num}")
                    SESS.pop(f"cloud:{num}", None)
                    continue
                handle_incoming(f"cloud:{num}", text)
    return {"ok": True}


@app.get("/api/health")
def health():
    """One-glance status for the UI and for whoever runs the server."""
    return {"ok": True, "llm": llm_ready(), "model": MODEL, "public": PUBLIC,
            "whatsapp": {"bridge": wa_status().get("state"), "cloud": cloud_ready()}}


@app.get("/api/wa/status")
def wa_state():
    s = wa_status()
    s["mirror"] = WA["on"]
    s["neighbors_shown"] = WA["neighbors"]
    s["cloud"] = cloud_ready()
    return s


@app.post("/api/wa/mirror")
def wa_mirror():
    d = request.get_json(force=True) or {}
    if "on" in d:
        WA["on"] = bool(d["on"])
    if "neighbors" in d:
        WA["neighbors"] = bool(d["neighbors"])
    return {"on": WA["on"], "neighbors": WA["neighbors"]}


@app.get("/api/wa/friends")
def friends_get():
    try:
        return bridge("/allow")
    except Exception:
        return {"numbers": []}


@app.post("/api/wa/friends")
def friends_set():
    d = request.get_json(force=True) or {}
    try:
        return bridge("/allow", {k: d[k] for k in ("add", "remove") if k in d})
    except Exception:
        return {"numbers": [], "error": "bridge off"}


import street as street_mod                      # six-neighbor visual street (website): /street
STREET = street_mod.make_blueprint(chat, MODEL, SIM_MODEL, cur_sid, PUBLIC)
app.register_blueprint(STREET)


@app.get("/")
@app.get("/street")
def street_page():
    return send_from_directory(HERE / "static", "street.html", max_age=0)


def seed_joined():
    """Anyone the bridge already knows has messaged us first: they've joined, even if our saved state predates it."""
    try:
        known = set(json.loads((HERE / "bridge" / "jids.json").read_text(encoding="utf-8")))
    except Exception:
        return
    S = sess("me")
    S.setdefault("joined", set()).update(ph for ph, v in REAL.items() if v["number"] in known)


load_real()
load_state()
seed_joined()
if SESS.get("me", {}).get("held"):
    schedule_morning(SESS["me"])

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 5215)), threaded=True)
