# NearMind Street: WAICY submission pack

Part 1 is the project write-up (copy the sections you need into the submission form).
Part 2 is the demo-video script. Fill in the `[brackets]` yourself.

Team / author: `[name, age, school, country]`
Category: `[WAICY category]`
Repo: https://github.com/awsaalibdeh-a11y/Near-Mind (branch `local-app-street`, folder `local-app/`)

---

# Part 1: Project write-up

## One-line pitch

NearMind is an AI agent that lives on the roof of an apartment building and helps neighbors help each other:
you ask for a small favor, it quietly finds the one or two people who can actually help, and you get what you need,
without spamming the whole building.

## The problem

People in apartment buildings often live a few meters apart and still don't know each other. When you need a ladder,
a phone charger at midnight or jumper cables at 6 AM, your options are bad:

- buy something you'll use once,
- post in a building group chat and wake up or annoy fifty people,
- or just go without.

The help is usually right there, behind one of the doors. What's missing is someone who knows who to ask, when it's
polite to ask, and how to ask.

## The solution

NearMind is that someone. A neighbor sends one message ("Need a ladder to change a ceiling bulb") and the agent:

1. **Understands** the request: what the item is, whether it's a borrow, a sale or company, and how urgent it is.
2. **Routes** it: picks the few neighbors most likely to have it and be awake, and asks each of them in a short,
   friendly message.
3. **Clarifies**: reads vague answers ("maybe, what's it like?"), asks follow-ups, and compares the offers.
4. **Hands over**: recommends the best offer to the asker, lets the asker decide, thanks and releases everyone else,
   and confirms the meeting place.

The website shows all of this as a live animated building: every message flies as a bubble from an apartment up to
the robot on the roof and back down, and when a deal closes the item travels door to door and the camera zooms to
the receiver's door.

## What you see in the demo

A ten-apartment building (five floors, two flats each) with ten neighbors, each a separately simulated AI person:

| Apt | Neighbor | Personality and what they own (privately) |
|---|---|---|
| 1A | Sedra 🎬 | movie lover |
| 1B | Osama 🧂 | kitchen basics |
| 2A | Sulaiman 🔧 | handyman: tools, ladder |
| 2B | Asma 🩹 | first aid, tea, kind |
| 3A | Alwalid 🍲 | cook, father of young kids |
| 3B | Anas 🎮 | gamer, night owl |
| 4A | Layla 🧵 | retired teacher, sewing kit, books |
| 4B | Yousef 🚴 | engineer, bike gear, tent, car |
| 5A | Noor 🧁 | pastry chef, baking tools, a cat |
| 5B | Hamza ⚽ | PE coach, car, jumper cables |

Five recorded real runs (replayed without calling the model, so they always work on stage):

| Demo | Who asks | Who the robot contacted | Result |
|---|---|---|---|
| 🎬 Movie night (19:30) | Sedra | Alwalid, Anas | Alwalid joins at 20:30 |
| 🪜 Ladder at noon | Osama | Sulaiman, Asma | Sulaiman's ladder at his door |
| 🔌 Charger after midnight | Anas | Sedra | Sedra lends a USB-C charger |
| 🚲 Selling a bike (17:00) | Asma | Sulaiman, Yousef | Yousef buys it for 150 SAR |
| 🚗 Jump-start at 6 AM | Noor | Asma, Hamza, Sulaiman | Hamza brings cables; Yousef was asleep and not disturbed |

You can also type any request live, change the time of day (the sky changes and people go to sleep), or switch to
**Sell** mode to list something with a price.

## How the AI works

- **One router agent (the robot).** Every turn it reads the conversation and returns strict JSON: a short "think"
  line, what it understood (`item`, `kind`, `price`, `urgency`), who to message and what to say, and a status for each
  neighbor (asked, has it, no, chosen). The server validates this: the robot cannot message unknown people, cannot
  mark the asker, and its outputs are checked before anything is shown.
- **Ten simulated neighbors.** Each neighbor is a separate model call with its own personality, sleep hours, budget,
  wish list and a **private inventory** the router never sees. So the robot really has to ask to find out, just like
  in real life. Neighbors only offer what is on their list. If it isn't there, they say no kindly.
- **Streaming.** The server streams events (NDJSON) to the page as they happen; the animated scene (built with
  Remotion) turns each event into motion: scanning lines when the robot decides, message packets with trails, status
  pills, opening doors.
- **Model:** an OpenAI chat model in JSON mode (`gpt-6.1-terra`).
- **Also built:** a WhatsApp version that runs the same engine on real chats. It is switched off for the competition
  demo, and has strict safety rules (it never starts a chat, never auto-replies in private chats, holds messages
  during quiet hours 22:00 to 08:00, anyone can send `stop`).

## Responsible AI, by design

These are rules in the code, not just in the prompt:

- **Privacy first.** The router sees only public facts (name, apartment, sleep hours), never what anyone owns.
  Neighbors never see each other's chats.
- **Ask as few people as possible.** The prompt forbids messaging everyone, and the on-screen **Neighbors contacted**
  card makes it measurable: for example "3 of 9 · 6 left in peace". Across the five demos the robot contacted
  1 to 3 of 9 neighbors each time.
- **Respect sleep.** People inside their sleep hours are skipped unless the request is urgent (in the 6 AM demo,
  Yousef is asleep and the robot doesn't wake him).
- **Honesty.** The robot only relays what neighbors actually said. During testing a simulated neighbor invented
  jumper cables he didn't own; we tightened the rules so neighbors can only offer real items, and re-recorded.
- **The human decides.** The robot recommends, but the asker chooses, and everyone not chosen is thanked and released.
- **Explainable.** Every step is visible: the robot's reasoning line, each message, each status, in the animation
  and in the timeline next to it.

## Testing

41 automated tests (`pytest`) cover the engine with the model faked: event order, the robot not being able to
message unknown people, bad requests, model failures turning into a clean error, every portrait being served, and
every recorded demo ending in a real handover.

## What's original

- An agent whose job is to **bother as few people as possible**, and shows you that number.
- Hidden information: the router doesn't know who owns what, so the demo shows real search and negotiation instead
  of a lookup.
- The whole conversation as an animated building you can watch, not a chat log.

## Impact

Sharing instead of buying saves money and waste, and small favors are how neighbors become a community.
NearMind lowers the cost of asking: one message instead of knocking on doors, and no one gets spammed.
It's useful for students, elderly neighbors who live alone, and new families who don't know anyone yet.

## Limitations and next steps

- The neighbors in the demo are simulated. Next: pilot the WhatsApp version with real neighbors who opt in.
- Trust and safety for strangers: verified residents, ratings, and building-manager controls.
- Arabic and English in the same building.
- Learning over time who usually helps with what, without storing private inventories.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY
python app.py               # http://127.0.0.1:5215
```

Shortcuts on the page: `1`-`5` play the demos, `P` present (full screen), `I` how it works, `S` speed, `R` reset,
`Esc` exits.

---

# Part 2: Demo-video script (about 3 minutes)

Setup before recording:
- Open http://127.0.0.1:5215 in a full-screen browser at 1920x1080. Close other tabs and notifications.
- Record the screen plus your voice (OBS, or Windows Game Bar `Win+Alt+R`).
- Do one rehearsal: press `R` to reset between takes.
- Check the current WAICY rules for the maximum video length. A 90-second cut is at the end.

| Time | On screen | What you do | Voice-over |
|---|---|---|---|
| 0:00-0:15 | The building at night, the robot on the roof | Page already open, press `R` | "This is a building with ten families. They live a few meters apart, but when one of them needs a ladder, a charger, or help at 6 AM, they don't know who to ask. So they buy something new, or spam a group chat, or go without." |
| 0:15-0:35 | **How it works** panel | Press `I`, scroll slowly, then `Esc` | "I built NearMind: an AI agent on the roof. You send it one message. It understands what you need, finds the few neighbors who can help and are awake, talks to them, and arranges the handover. And it's designed to bother as few people as possible." |
| 0:35-0:40 | Full-screen building | Press `P` | "Let's watch it work." |
| 0:40-1:35 | 🚗 Jump-start demo | Press `5` | (as Noor's bubble rises) "It's 6 AM. Noor's car battery is dead and she has an early shift." (scan lines) "The robot scans the building. It can't see what anyone owns, that's private, so it has to reason about who might have jumper cables and who's awake." (packets fly) "It asks only three people. Yousef is asleep, so it leaves him alone." (replies) "Sulaiman and Asma don't have cables, but they offer help. Hamza does." (Noor picks Hamza) "The robot recommends Hamza, but Noor makes the choice. Everyone else gets thanked and released." (zoom to door) "And the cables arrive at Noor's door." |
| 1:35-1:45 | Zoom on the **Neighbors contacted** card | Pause on it | "Three of nine contacted. Six neighbors left in peace. That number is the point." |
| 1:45-2:20 | 🚲 Selling a bike | Press `Esc`, then `4` (press `S` for 2× if you're short on time) | "It also works for selling. Asma wants to sell her bike for 150 riyals. The robot finds the two neighbors who'd actually want a bike, answers their questions, and closes the deal with Yousef, at his door." |
| 2:20-2:40 | The timeline beside the building | Scroll the timeline | "Every step is visible: what the robot was thinking, every message, every decision. Nothing happens behind your back." |
| 2:40-2:55 | The **How it works** panel, responsible-AI part | Press `I` | "It's responsible by design: it never sees inventories, neighbors never see each other's chats, it respects sleep, it only repeats what people really said, and the human always decides. There's also a WhatsApp version with strict rules: it never starts a chat." |
| 2:55-3:05 | Building, robot blinking | `Esc` | "NearMind: one message, the right neighbor, everyone else left in peace. Thank you." |

## 90-second cut

0:00-0:10 problem (first line above) → 0:10-0:20 "I built NearMind..." over `I` → 0:20-1:10 jump-start demo
(`P`, `5`, `S` for 2×) → 1:10-1:20 the "3 of 9, six left in peace" card → 1:20-1:30 responsible-AI line and
closing sentence.

## Tips

- Speak slowly; let each bubble land before you describe it. Use `S` for 2× only where you need to save time.
- If something goes wrong live, press `R` and the demo number again; the demos are recorded, so they replay the same way.
- Say "simulated neighbors" once, clearly. Judges value honesty about what's real.
