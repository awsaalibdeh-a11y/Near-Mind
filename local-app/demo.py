"""NearMind demo: plays one neighborhood-favor scenario as WhatsApp messages.

Dry run (default): prints the chat. Nothing is sent.
  python demo.py

Send to YOUR OWN WhatsApp via Twilio sandbox (set in .env, see .env.example):
  python demo.py --send
"""
import os, sys, time

# (sender, text). NearMind is the agent; A/B/C are neighbors with different styles.
SCENARIO = [
    ("Maya (Neighbor A)", "anyone have salt?? halfway through dinner and out 😅"),
    ("NearMind", "Got it Maya. Need: salt, about 1 tsp, urgent (dinner in progress). "
                 "Fine substitutes: table, sea, or kosher salt. Checking with Ben (#12) and Mrs. Cohen (#14) now."),
    ("NearMind → Ben (Neighbor B, casual & brief)",
     "hey Ben! Maya next door needs a little salt for dinner. any kind works. got some to spare? no stress if not 🙂"),
    ("NearMind → Mrs. Cohen (Neighbor C, warm & formal)",
     "Good evening Mrs. Cohen. Maya at #10 is short of salt for tonight's dinner and would be grateful for a spoonful of any kind. "
     "Only if it's no trouble at all, and thank you either way."),
    ("Ben (Neighbor B)", "got the pink stuff"),
    ("Mrs. Cohen (Neighbor C)", "Only the coarse baking kind, dear. Give me 5 minutes and I'll find a jar."),
    ("NearMind (clarifying Ben)",
     "Ben, quick check: 'pink stuff' = Himalayan pink salt? It's fine for cooking (same taste, just coarser). Good to hand over?"),
    ("Ben (Neighbor B)", "yep himalayan. grinder, ok to grab"),
    ("NearMind (clarifying Mrs. Cohen)",
     "Mrs. Cohen, 'coarse baking kind' = coarse kosher salt? That works well too; a small cup is plenty."),
    ("NearMind → Maya (Neighbor A, casual & brief)",
     "Two offers, Maya 🎉\n"
     "• Ben (#12): Himalayan pink salt in a grinder, ready now, same taste, just grind it\n"
     "• Mrs. Cohen (#14): coarse kosher salt, ready in ~5 min (use ~1.5x the amount, it's chunkier)\n"
     "Ben is faster. Want me to lock it in with him?"),
    ("Maya (Neighbor A)", "ben pls!!"),
    ("NearMind → Ben (Neighbor B, casual & brief)",
     "Maya says yes please 🙏 Porch drop at #10 okay? She'll leave the light on. Ring once, no need to chat."),
    ("Ben (Neighbor B)", "on my way 👍"),
    ("NearMind → Mrs. Cohen (Neighbor C, warm & formal)",
     "Mrs. Cohen, Ben already had some on hand, so there's no need to trouble yourself tonight. "
     "Maya sends her warmest thanks and would love to bring you a slice of dessert tomorrow."),
    ("NearMind → Maya (Neighbor A, casual & brief)",
     "Done ✅ Ben's dropping the grinder on your porch in ~2 min. Maybe return it with a thank-you? Want me to remind you tomorrow?"),
]


def send_whatsapp(body: str):
    from twilio.rest import Client  # pip install twilio
    c = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    c.messages.create(from_=os.environ["TWILIO_WHATSAPP_FROM"],  # whatsapp:+14155238886
                      to=os.environ["MY_WHATSAPP"],               # whatsapp:+<your number>
                      body=body)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    send = "--send" in sys.argv
    for who, text in SCENARIO:
        line = f"*{who}*\n{text}"
        print(line, "\n")
        if send:
            send_whatsapp(line)
            time.sleep(2.5)  # keep order + feel like a live chat


if __name__ == "__main__":
    main()
