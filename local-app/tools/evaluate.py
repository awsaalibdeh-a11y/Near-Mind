"""Score NearMind on a fixed set of real requests, with the live model, and write the results.

Usage (server running on :5215):  python tools/evaluate.py [label]
Writes waicy/eval-<label>.json and prints a summary table. Each scenario: the asker sends the request, then accepts the
robot's recommendation (its first quick reply, or "yes please"), for up to 3 turns, like a real person would.

What it measures, per request:
  closed      the request ended with a handover (someone chosen, phase closed)
  contacted   how many neighbors the robot messaged (fewer is better; 1-3 is the design)
  woke        neighbors messaged while probably asleep although the request wasn't urgent (should be 0)
  same_lang   for an Arabic request, every message to the asker was in Arabic
  messages, rounds, seconds, errors
"""
import json
import pathlib
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import street  # noqa: E402  (only to read buildings and sleep hours; no server is started)

BASE = "http://127.0.0.1:5215"
ARABIC = re.compile(r"[؀-ۿ]")

# (building, asker or None for the building's first family, clock, request)
ONLY = None   # set by "--only 0,9" to rerun some scenarios
SCENARIOS = [
    ("noor-tower", "noor", "06:00", "my car battery is dead and i have an early shift, anyone have jumper cables?"),
    ("noor-tower", "osama", "13:00", "Need a ladder to change a ceiling bulb"),
    ("noor-tower", "anas", "00:30", "my phone is dying, anyone have a usb-c charger?"),
    ("noor-tower", "sedra", "19:30", "I need someone to watch a movie with me tonight"),
    ("noor-tower", "asma", "17:00", "I'm selling my old adult bike, solid frame and good wheels, for 150 SAR",
     "It's a hybrid, the brakes and gears work fine. Whoever is keen at 150 can have it, I'll bring it to their door."),
    ("coral-view", None, "10:00", "Can I borrow a cup of sugar? I'm baking for my kids"),
    ("saffron-house", None, "11:00", "Does anyone have a drill I can borrow for 10 minutes? Putting up a shelf"),
    ("moonrise-heights", None, "20:00", "Anyone up for board games this evening?"),
    ("skyline-lofts", None, "02:00", "My son has a high fever, does anyone have a thermometer?"),
    ("cardamom-court", None, "16:00", "Selling a desk lamp, works great, 40 SAR",
     "It's adjustable, with warm and white light, no USB port. Happy to sell at 40 to whoever wants it, I can bring it over."),
    ("atlas-hall", None, "09:00", "صباح الخير، ممكن أستلف مكواة ملابس لمدة نص ساعة؟"),
    ("pearl-tower", None, "08:00", "It's pouring outside and I have to walk to work, can I borrow an umbrella?"),
]


def post(path, body, sid):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "X-Sid": sid})
    with urllib.request.urlopen(req, timeout=400) as r:
        return [json.loads(line) for line in r.read().decode("utf-8").splitlines() if line.strip()]


def one(i, sc, label):
    bid, asker, clock, text = sc[:4]
    details = sc[4] if len(sc) > 4 else None
    B = street.BUILDINGS[bid]
    asker = asker or B["order"][0]
    sid = f"eval-{label}-{i}-{int(time.time())}"
    post("/api/street/reset", {"building": bid}, sid)
    events, msg, t0 = [], text, time.time()
    apt, answered = None, False
    for _turn in range(4):
        ev = post("/api/street/run", {"from": asker, "text": msg, "clock": clock, "building": bid}, sid)
        events += ev
        if any(e["t"] == "phase" and e["phase"] == "closed" for e in ev):
            break
        quick = next((e["options"] for e in reversed(ev) if e["t"] == "quick"), None)
        arabic = bool(ARABIC.search(text))
        last = next((e["text"] for e in reversed(ev) if e["t"] == "say" and e["from"] == "robot" and e["to"] == asker), "")
        apt = B["N"][asker]["apt"]
        # a realistic asker: answers the robot's question (details, where, when), otherwise accepts its recommendation
        if "?" in last and not quick and not answered:
            msg = details or (f"نعم من فضلك. أنا في شقة {apt}، أي وقت خلال ربع ساعة يناسبني." if arabic
                              else f"Yes please. I'm at apartment {apt}, any time in the next 15 minutes works for me.")
            answered = details is None                    # the generic answer is given once; details first if there are any
            details = None
        else:
            msg = quick[0] if quick else ("نعم من فضلك، خلنا نمشي مع اقتراحك" if arabic else "Yes please, go with your recommendation")
    secs = round(time.time() - t0)
    h, m = (int(x) for x in clock.split(":"))
    hf = h + m / 60
    parse = next((e for e in reversed(events) if e["t"] == "parse"), {})
    urgent = parse.get("urgency") == "high"
    reached = {e["to"] for e in events if e["t"] == "say" and e["from"] == "robot" and e["to"] != asker}
    woke = sorted(n for n in reached if street.asleep(n, hf, B["N"])) if not urgent else []
    to_asker = [e["text"] for e in events if e["t"] == "say" and e["from"] == "robot" and e["to"] == asker]
    arabic_req = bool(ARABIC.search(text))
    return {
        "building": bid, "asker": asker, "clock": clock, "request": text, "urgency": parse.get("urgency", ""),
        "closed": any(e["t"] == "phase" and e["phase"] == "closed" for e in events)
                  and any(e["t"] == "status" and e["state"] == "chosen" for e in events),
        "contacted": len(reached), "woke": woke,
        "same_lang": (all(ARABIC.search(t) for t in to_asker) if to_asker else False) if arabic_req else None,
        "messages": sum(e["t"] == "say" for e in events), "rounds": sum(e["t"] == "think" for e in events),
        "errors": [e["error"] for e in events if e["t"] == "error"], "seconds": secs,
        "log": [f"{e['from']} -> {e['to']}: {e['text']}" if e["t"] == "say" else f"[{e['t']}] {e.get('phase') or e.get('state', '')} {e.get('who', '')}".strip()
                for e in events if e["t"] in ("say", "phase", "status")],
    }


def main():
    global ONLY
    args = sys.argv[1:]
    if "--only" in args:
        k = args.index("--only"); ONLY = {int(x) for x in args[k + 1].split(",")}; del args[k:k + 2]
    label = args[0] if args else "run"
    picked = [(i, sc) for i, sc in enumerate(SCENARIOS) if ONLY is None or i in ONLY]
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda a: one(a[0], a[1], label), picked))
    out = ROOT / "waicy" / f"eval-{label}.json"
    n = len(res)
    summary = {
        "requests": n,
        "closed_with_handover": sum(r["closed"] for r in res),
        "avg_neighbors_contacted": round(sum(r["contacted"] for r in res) / n, 2),
        "max_neighbors_contacted": max(r["contacted"] for r in res),
        "woke_someone_needlessly": sum(bool(r["woke"]) for r in res),
        "arabic_answered_in_arabic": [r["same_lang"] for r in res if r["same_lang"] is not None],
        "avg_messages": round(sum(r["messages"] for r in res) / n, 1),
        "avg_ai_rounds": round(sum(r["rounds"] for r in res) / n, 1),
        "errors": sum(len(r["errors"]) for r in res),
        "avg_seconds": round(sum(r["seconds"] for r in res) / n),
    }
    out.write_text(json.dumps({"label": label, "summary": summary, "runs": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'building':18} {'asker':9} {'time':5} closed contacted woke  secs  request")
    for r in res:
        print(f"{r['building']:18} {r['asker']:9} {r['clock']:5} {str(r['closed']):6} {r['contacted']:^9} {len(r['woke']):^4} {r['seconds']:5}  {r['request'][:48]}")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
