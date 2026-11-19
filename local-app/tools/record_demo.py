"""Record a real NearMind Street run into static/demos/<name>.json so the site can replay it instantly.

Usage (server running on :5215):  python tools/record_demo.py
Each scenario: the asker's request, then the asker accepts the robot's suggestion, until the request closes (max 3 turns).
"""
import json
import pathlib
import urllib.request

BASE = "http://127.0.0.1:5215"
OUT = pathlib.Path(__file__).resolve().parent.parent / "static" / "demos"
SCENARIOS = [
    ("movie", "Movie night", "sedra", "19:30", "I need someone to watch a movie with me tonight"),
    ("ladder", "A ladder at noon", "osama", "13:00", "Need a ladder to change a ceiling bulb"),
    ("charger", "Charger after midnight", "anas", "00:30", "my phone is dying, anyone have a usb-c charger?"),
    ("sale", "Selling a bike", "asma", "17:00", "I'm selling my old adult bike, solid frame and good wheels, for 150 SAR"),
    ("jump", "Jump-start at 6 AM", "noor", "06:00", "my car battery is dead and i have an early shift, anyone have jumper cables?"),
    ("arabic", "Ladder, in Arabic", "noor", "18:00", "مرحبا، أحتاج سلم صغير لتغيير لمبة في المطبخ، هل عند أحد؟"),
]


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return [json.loads(line) for line in r.read().decode("utf-8").splitlines() if line.strip()]


FOLLOWUPS = {   # what the asker says next when the robot needs more than a yes
    "movie": ["Alwalid sounds perfect! Let's say 20:30 at my place, apartment 1A, after his kids are asleep. Can you confirm that with him now?"],
    "jump": ["Hamza please, he's the fastest!",
             "My car is in the basement parking, spot B4 next to the lift. I'll be there with the bonnet open. Thank you!"],
    "arabic": ["نعم، سليمان من فضلك. أنا في شقة 5A، أقدر أجي آخذه الحين.",
               "تمام، شكراً جزيلاً!"],
    "sale": ["It's a medium hybrid, a bit dusty but no rust, and the brakes and gears work fine. Whoever is keen at 150 can have it.",
             "Yes, Sulaiman. 150 SAR, I'll bring it to his door myself tomorrow at 18:30.",
             "Yes, I'll bring it myself. Thanks!"],
}


def record(name, title, asker, clock, text):
    post("/api/street/reset", {})
    events, msg, follow = [], text, list(FOLLOWUPS.get(name, []))
    for turn in range(4):
        ev = post("/api/street/run", {"from": asker, "text": msg, "clock": clock})
        events += [e for e in ev if e["t"] != "done"]
        if any(e["t"] == "phase" and e["phase"] == "closed" for e in ev):
            break
        quick = next((e["options"] for e in reversed(ev) if e["t"] == "quick"), None)
        msg = follow.pop(0) if follow else (quick[0] if quick else "Yes please, go with your recommendation")
    events.append({"t": "done"})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps({"title": title, "asker": asker, "clock": clock, "events": events},
                                                 ensure_ascii=False, indent=0), encoding="utf-8")
    says = sum(e["t"] == "say" for e in events)
    closed = any(e["t"] == "phase" and e["phase"] == "closed" for e in events)
    print(f"{name}: {says} messages, closed={closed}")


if __name__ == "__main__":
    import sys
    pick = set(sys.argv[1:])
    for sc in SCENARIOS:
        if not pick or sc[0] in pick:
            record(*sc)
