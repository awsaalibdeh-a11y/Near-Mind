# NearMind Street

**The agent that makes neighbors neighborly.** Six neighbors live in one building with the NearMind robot on the roof.
Any of them can ask for a small favor ("I need a ladder", "anyone up for a movie?"). The robot works out who is likely
to have it and awake, asks them in their own style, untangles vague replies, recommends the best offer and arranges the
handover. Every message is animated: you watch each bubble travel from an apartment up to the robot and back down.

The neighbors (all AI models): **Sedra** 🎬, **Osama** 🧂, **Sulaiman** 🔧, **Asma** 🩹, **Alwalid** 🍲, **Anas** 🎮.
Portraits and backdrop are illustrated with Higgsfield; the animation is a live Remotion scene.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY (model: NM_MODEL, here gpt-6.1-terra)
python app.py               # http://127.0.0.1:5215
```

- Pick who's asking (tap an apartment or a chip), type a request or tap a preset, and watch it play out.
- Time-of-day chips change the sky and who's asleep; the live timeline lists every step.
- **Sell** mode: a neighbor lists something with a price; the robot finds who'd want it and the item goes to the buyer's door.
- **Watch a demo** replays recorded real runs instantly (no model calls). Re-record with `python tools/record_demo.py`.
- When a deal closes, the item travels door to door and the camera zooms in on the receiver's door. `1×/2×` sets the pace.
- Rebuild the animation after editing `remotion/src/street.jsx`: `cd remotion && npm install && node build.mjs`.

## WhatsApp (off for now)

The WhatsApp link is switched off; the page shows it on the side. When on, it runs the WhatsApp engine below.

`start-whatsapp.bat` runs `bridge/bridge.js`, which links to **your own WhatsApp** as a linked device (pairing code on
first run, shown in the app's WhatsApp panel).

- **Talk to NearMind** in your "Message yourself" chat. That chat is private: it shows only you and NearMind. Tick
  *Also show its chats with neighbors* in the panel to see everything.
- **Real neighbors**: in the panel, put a real person in a neighbor slot (name and number). They send your number any
  message once to join; after that NearMind asks them for favors and their real replies drive it.
- **Friends** you add can use NearMind from their own WhatsApp, with an AI street of their own.

Commands in the chat:

| Command | What it does |
|---|---|
| `/status` | who's on your street (real or AI, joined or not), the open request, what you owe |
| `/new` | fresh request; NearMind keeps what it learned |
| `/send` | deliver messages held for quiet hours now |
| `/reset` | forget everything (asks you to reply *yes*); opt-ins are kept |
| `/help` | the list |

**Real-neighbor etiquette, enforced in code:**
- NearMind never auto-replies in someone's private chat with you. It reads a neighbor's message only while it is waiting for
  their answer to its own question; anything else stays between you and them.
- Quiet hours (`NM_QUIET_START`/`NM_QUIET_END`, default 22-08): messages to real neighbors are held and sent at 08:00, unless
  the request is urgent. `/send` sends them now.
- No answer within `NM_REPLY_TIMEOUT_MIN` (default 15) minutes: NearMind tells you instead of waiting forever.
- The building view shows each real neighbor's live status: joined, awaiting reply, held, or not joined yet.

**Safety rules, enforced in code:** the bridge never starts a chat. It only messages you, or people who are on your list
**and** have messaged you first. Anyone can send `stop` to be removed. Groups are ignored.

### Meta Cloud API (optional)

To give NearMind its own number instead of yours, set `META_TOKEN`, `META_PHONE_ID` and `META_APP_SECRET` in `.env` and
point the Meta webhook at `/api/wa/cloud` (through the tunnel in `tunnel/`). A test number can only message recipients
verified in the Meta dashboard, and free text only within 24h of their last message.

## Files

| Path | What |
|---|---|
| `street.py` | the six-neighbor engine and its streaming API (`/api/street/*`) |
| `static/street.*`, `static/img/` | the website, portraits and backdrop |
| `remotion/src/street.jsx` | the animated building (built to `static/street-scene.js`) |
| `app.py` | Flask server: serves the site, plus the WhatsApp engine, commands and persistence |
| `bridge/` | WhatsApp linked-device bridge (Baileys) |
| `state.json` | NearMind's memory of your street (created at runtime) |
| `neighbors.json` | real neighbor slots (created at runtime) |

`state.json`, `neighbors.json`, `.env` and `bridge/auth`, `allow.json`, `jids.json` hold personal data and are git-ignored.

## Tests

```bash
python -m pytest -q test_street.py test_app.py test_real_neighbors.py   # street, server, WhatsApp engine
python test_cloud_fake.py                                # Meta Cloud webhook against a fake Meta
```

No test touches WhatsApp or OpenAI: the model and the bridge are faked.

## Health

`GET /api/health` reports whether the model key is set, the model in use, and the bridge and Cloud status.
