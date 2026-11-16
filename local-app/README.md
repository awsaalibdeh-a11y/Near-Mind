# NearMind

**The agent that makes neighbors neighborly.** Ask for a small favor ("anyone have a ladder?") and NearMind works out
who on your street is likely to have it and awake, asks them in their own style, untangles vague replies ("the long
thing in the garage"), recommends the best offer and arranges the handover. It remembers who helped and what you owe.

Neighbors can be **AI-played** (Ben, Mrs. Cohen, Omar) or **real people on WhatsApp**.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY
run.bat                     # starts the WhatsApp bridge and the app on http://127.0.0.1:5215
```

- **Showcase** plays scripted scenarios and needs no API key. Keys: Space play/pause, → step, R replay, S speed.
- **Live** talks to the real model (`NM_MODEL`, default `gpt-5-mini`; this install uses `gpt-6.1-terra`).

## WhatsApp

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
| `app.py` | Flask server: agent loop, neighbor simulation, WhatsApp routing, commands, persistence |
| `static/` | web app (`app.js`, `app.css`, `apt.js` apartment view) |
| `bridge/` | WhatsApp linked-device bridge (Baileys) |
| `state.json` | NearMind's memory of your street (created at runtime) |
| `neighbors.json` | real neighbor slots (created at runtime) |

`state.json`, `neighbors.json`, `.env` and `bridge/auth`, `allow.json`, `jids.json` hold personal data and are git-ignored.

## Tests

```bash
python -m pytest -q test_app.py test_real_neighbors.py   # server, real neighbors, commands, persistence
python test_cloud_fake.py                                # Meta Cloud webhook against a fake Meta
```

No test touches WhatsApp or OpenAI: the model and the bridge are faked.

## Health

`GET /api/health` reports whether the model key is set, the model in use, and the bridge and Cloud status.
