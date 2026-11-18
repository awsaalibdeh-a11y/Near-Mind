# NearMind: WAICY 2026 submission pack (LLM & AI Agent Track)

**Author:** Aws Alaa, 13, Grade 8, Al Safi International Language School, Saudi Arabia
**Track:** LLM & AI Agent Track (theme: *AI as a Service*)
**Project:** NearMind, an AI neighborhood-sharing agent
**Code:** https://github.com/awsaalibdeh-a11y/Near-Mind (branch `local-app-street`, folder `local-app/`)

---

## Part 0: The official rules (checked 17 Nov 2026)

Sources: the [WAICY 2026 Guidebook](https://waicy-cdn.wholeren.cn/wp-content/uploads/2026/10/WAICY-2026-Guidebook-2.pdf)
and the [WAICY 2026 Rubrics](https://www.waicy.org/rubrics/) page.

| Rule | What it says |
|---|---|
| Deadline | **29 November 2026, 5:00 PM ET** (01:00 on 30 Nov, Saudi time) via the online submission form |
| Who | Teams of 1-5, under 18. Individual entry is fine. Free. Language: English |
| Selected teams announced | 2 December |
| WAICY Day (live, online) | 4-6 December; winners announced 7 December |
| Track theme | *AI as a Service*: turn a general LLM into a specialized, personalized advisor/agent that adapts to different users |
| Age categories | None in this track (all ages judged together) |
| What to submit | **One PDF**, shared in a Google Drive folder the judges can open |
| File naming | Folder `LLM_Middle_NearMind`, file `LLM_Middle_NearMind.pdf` (format `Track_Category_ProjectName`; Grade 8 = Middle) |
| Video | Not required for this track. The video script below is for WAICY Day if you're selected, or as optional extra material |

**What the PDF must contain** (in this order, this pack follows it):
1. What specific service your AI provides
2. Who your users are: **at least 3 different user profiles**
3. Motivation
4. Link to the chat history: **at least 10 messages** with the final version
5. Link to the chatbot: **a live link judges can use**
6. Iterative design process: Idea → Advisor Design → Testing → Error Analysis → Improvement
7. Limitations
8. Future development
9. Conclusion
10. References (APA, MLA or Chicago)

**How it's scored (100 points):**

| Criterion | Points |
|---|---|
| Specific AI Service (clear, detailed function and purpose) | 25 |
| Iterative Development (idea evolution, prompt refinement, experimental results) | 25 |
| Motivation & Problem Statement | 10 |
| Limitations & Considerations (ethics, unintended consequences) | 10 |
| Future Development & Clear Reference (and a strong conclusion) | 10 |
| Presentation & Communication (live presentation and Q&A) | 10 |
| Originality & Creativity | 10 |

The guidebook also says tools, APIs and agentic behavior are welcome, but judged on whether they *meaningfully* improve
the solution, not on complexity alone. Its tips: be specific, design for different people, ask before advising, try to
make your AI fail, and know when to say "I don't know". NearMind already does all of these; the PDF should say so.

### Still missing before you can submit

- [ ] **Live chatbot link.** It runs from your own computer: double-click `start-public.bat` and copy the
      `https://....trycloudflare.com` address it shows. **Rules for keeping it working:**
      - Start it once, shortly before you submit, and **don't close it** until WAICY is over (7 December).
        Every restart gives a **new address**, and the one in your PDF would stop working.
      - The computer must stay **on, plugged in, online and awake**. Windows Settings → System → Power →
        set "When plugged in, put my device to sleep after" to **Never**. Don't restart for Windows updates
        (Settings → Windows Update → Pause updates).
      - Set a monthly spending limit in the OpenAI dashboard, in case the link gets shared.
- [ ] **Chat history link.** The same address + `/chat/jump` shows the full 6 AM jump-start conversation
      (16 messages, 3 of 9 neighbors contacted). The other four runs are at `/chat/ladder`, `/chat/charger`,
      `/chat/sale` and `/chat/movie`.
- [ ] Open both links on a phone using mobile data (not your home Wi-Fi) before submitting, to be sure they work
      from outside. If the computer ever has to restart, the link changes: you'd need to tell WAICY the new
      one (info@waicy.org), so try hard not to.
- [ ] **Screenshots** for the PDF: the building, a demo mid-way, the "Neighbors contacted" card, the delivery zoom.
- [ ] Turn this text into the PDF, upload it to a Google Drive folder named `LLM_Middle_NearMind`, set sharing to
      "anyone with the link can view", and submit the form at https://www.waicy.org/2026-submission
- [ ] Optional: Saudi Arabia also has **WAICY KSA** (ages 13-18, finals in Abha) at https://www.waicy.org/waicy-2026-ksa/.
      Ask your school whether it's open and how it relates to WAICY Global.

---

## Part 1: The PDF text

### 1. What specific service NearMind provides

**NearMind is a neighborhood-sharing agent for one apartment building.** A resident sends one message, such as
"Need a ladder to change a ceiling bulb", "my phone is dying, anyone have a USB-C charger?" or "I'm selling my old
bike for 150 SAR". NearMind finds the one or two neighbors who can actually help, talks to them, and arranges the
handover, without spamming the whole building.

It is deliberately narrow. It is not a general assistant, and not a marketplace. Each building has its own robot,
which only connects the 10 families inside that building. To show it scales, the demo is a whole simulated city:
**NearMind City, with 5 neighborhoods, 20 buildings, 200 families and 1,182 people** (4-8 per apartment: parents,
sons, daughters, grandparents), with no name repeated anywhere. You tap a neighborhood on the city map, then a
building, then an apartment. It handles four kinds of request inside a building:

| Kind | Example |
|---|---|
| Borrow an item | a ladder, a charger, jumper cables |
| A small favor | help with a dead car battery at 6 AM |
| Company | someone to watch a movie with tonight |
| Sell something | a bike for 150 SAR, delivered to the buyer's door |

**What it does, step by step** (this is written into its instructions):

1. **Understand** the request: item, quantity, urgency, sensible substitutes. If it's unclear, ask one short question
   first instead of guessing.
2. **Choose who to ask**: 1-3 neighbors most likely to have it **and** be awake, using only public facts (job,
   hobbies, sleep hours) and the time of day. Two normally; three only when urgent. Never everyone.
3. **Clarify** vague answers ("the long thing in the garage") with that neighbor before reporting back.
4. **Recommend** the best offer with a reason (fastest, safest, awake), and let the asker choose.
5. **Hand over**: confirm time and place with the chosen neighbor, thank and release the others, and close.

**The value:** you get what you need in minutes instead of buying something you'll use once, and the rest of the
building isn't disturbed. On screen, a counter shows it, for example "Neighbors contacted: 3 of 9 · 6 left in peace".

**How it's built:**
- **The agent (the robot on the roof)** is an LLM (`gpt-6.1-terra`, OpenAI JSON mode) with a detailed system prompt.
  Each turn it replies with one JSON object: a one-line "think" shown to the audience, what it understood
  (`item`, `kind`, `price`, `urgency`), which phase it's in, a status for each neighbor (asked, offer, no, chosen,
  released), **a short reason for each neighbor it picks** (shown on screen under "Why these neighbors?"), the
  messages to send, and up to three quick-reply buttons for the asker.
- **200 simulated families** test it. In each building, every apartment's contact person is a separate LLM call with
  its own personality, job, sleep hours, budget, wish list, family members and a **private inventory the agent never
  sees**. So the agent has to reason and ask, like in real life, rather than look things up. Families help too: a
  neighbor may say their teenage son can carry it down.
- **The city is generated by code** (`city.py`, fixed seed) with strict rules checked by tests: every neighborhood
  and building name is different, no first name repeats inside a building, every family name is different, and no
  two people in the city share a full name. Each building gets its own robot prompt with its own 10 families.
- **Code checks the agent:** the server ignores any message to an unknown person (or someone from another
  building), never lets it mark the asker, and turns model errors into a clean message instead of a crash. 45
  automated tests check this with the model faked.
- **The website** turns each step into animation: you watch every message fly between the apartments and the robot,
  and when a deal closes the item travels door to door. Portraits were illustrated with an AI image tool; the
  animation uses Remotion.

> *Screenshot here: the building at night with the robot on the roof.*

### 2. Who the users are

NearMind has to give different answers to different people. Four askers from the test building:

| User | Who they are | What they need | What NearMind must consider |
|---|---|---|---|
| **Noor, 5A** 🧁 | Pastry chef, early shifts | 06:00, her car battery is dead: jumper cables, now | **Urgent**, so asking 3 people is okay. Most neighbors are asleep: choose people who are awake and likely to have a car. Speed beats everything |
| **Asma, 2B** 🩹 | Kind neighbor, first-aid kit, tea | Sell her old bike for 150 SAR | She's the **seller**, so the agent looks for a **buyer**. Choose people whose interests fit (cycling, sport), check they're interested at the price, answer their questions, never pressure anyone. The bike goes to the buyer's door |
| **Sedra, 1A** 🎬 | Loves movies | Someone to watch a movie with tonight | It's **company**, not an item. Choose people who are free and sociable in the evening; agree on a time and place, and respect that some neighbors have small kids |
| **Osama, 1B** 🧂 | Kitchen basics, not a handyman | A ladder to change a ceiling bulb | A normal **borrow**. Ask 2 people at most; prefer the **safer** offer (a proper ladder over standing on a chair) and say why |

The **neighbors being asked** are users too, and they're different: Anas (19, student) sleeps until noon; Alwalid has
young kids; Yousef and Hamza have cars; Layla is retired and home a lot. NearMind writes to each in their own style,
skips people who are probably asleep unless it's urgent, and never shows one neighbor's chat to another.

### 3. Motivation

`[Write this in your own words. It counts for 10 points, and judges can tell. Some questions to answer:]`
- When did you or your family last need something small that a neighbor probably had? What did you do?
- Why apartment buildings? (In Saudi cities many families live in buildings and don't know their neighbors.)
- Why does it matter that the AI asks *as few people as possible*?
- What did you want to learn by building an agent, not just a chatbot?

Something like: "In my building, people live a few meters apart but barely talk. When my family needed
`[something]`, we `[bought it / went without]`, and later found out the neighbor upstairs had one. I wanted an AI
that knows who to ask, when it's polite to ask, and how to ask, so that neighbors help each other instead of
buying things they use once."

### 4. Link to the chat history

`https://<your-address>.trycloudflare.com/chat/jump`

The **jump-start at 6 AM** run (16 messages). Noor asks; NearMind asks Sulaiman ("retired mechanic, awake early"),
Hamza ("has a car, awake early") and Asma ("keeps emergency supplies"), and not Yousef, who's asleep. Sulaiman and
Asma don't have cables but offer other help; Hamza does. NearMind recommends Hamza and says why; Noor chooses and
says where her car is parked; NearMind confirms the place with Hamza, thanks the other two, and closes the request.

### 5. Link to the chatbot

`https://<your-address>.trycloudflare.com`

To keep it fair and affordable, each visitor gets their own private building, and there's a limit on live
requests per hour and per day. The five recorded demos always work.

How to use it: pick who's asking (tap an apartment), type a request or tap a preset, and watch it play out. Change
the time of day and the sky changes and people go to sleep. **Watch a demo** replays five recorded real runs
instantly. Keyboard: `1`-`5` demos, `I` how it works, `P` full screen, `S` speed, `R` reset.

### 6. Iterative design process

*(25 points: the biggest section. Add screenshots of before/after for each round.)*

**Idea.** An agent that sits between neighbors: you ask once, it asks the right people. The first version ran on
WhatsApp with real people, so it had strict safety rules from day one: it never starts a chat, never auto-replies in
someone's private chat, holds messages during quiet hours (22:00-08:00), and anyone can send "stop".

**Advisor design.**
- *Problem:* you can't test an agent like this safely on real neighbors at 3 AM.
  *Decision:* build a simulated building where every neighbor is an AI person with a private inventory.
- *Problem:* if the agent could see everyone's inventory, it would just look it up. That's not realistic and not
  private. *Decision:* the agent only gets **public facts** (job, hobbies, sleep hours, apartment). Its prompt says
  "use only the PUBLIC facts and clock below, never guess inventories".
- *Decision:* the agent answers in **strict JSON**, so the code can check every action, and the website can animate it.
- The building grew from 6 to **10 neighbors on 5 floors**, so that choosing who to ask became a real decision. Later it grew into a whole city of 200 families (round 9 below).

**Testing, error analysis and improvement.** Each round: run real requests, read every message, find what went
wrong, change the prompt or the code, and run again.

| # | What we tested | What went wrong (error analysis) | What we changed | Result |
|---|---|---|---|---|
| 1 | Growing from 6 to 10 neighbors | With more people to choose from, there was nothing stopping the agent from messaging lots of them, and nothing showed how many it bothered | Prompt: "Pick the 1-3 neighbors (out of all ten; asking fewer people is better: never message everyone)... Ask 2 normally; 3 only when urgent." Added the on-screen **Neighbors contacted** counter to measure it | In the five recorded demos it contacted 1-3 of 9 neighbors each time |
| 2 | Requests at night and early morning | Waking people up is rude | Each neighbor has sleep hours; the agent is told who is "probably ASLEEP" and the rule "don't ping someone who is probably asleep unless it's urgent". Sleeping neighbors reply sleepy and short | At 06:00 the agent skipped Yousef (asleep) |
| 3 | 6 AM jump-start | **A simulated neighbor made something up:** Sulaiman offered jumper cables that weren't in his inventory. The agent would have relayed a false offer | Neighbor prompt: "Be truthful about what you have: you ONLY own the things listed above; if something isn't listed, you don't have it, so say no kindly." Agent rule: "Only relay what neighbors actually said. Never invent that someone has something." | Re-ran: Sulaiman says no and offers to help push-start; Hamza, who really has cables, is chosen |
| 4 | Movie night | The conversation never finished: the agent kept saying it would check and come back | Found the agent was right to wait: it can't confirm a meeting without a time and place, and the test asker never gave one. The prompt already says to confirm "time and place" before closing, so the fix was in the test: the asker now proposes 20:30 at her flat | The request closes with Alwalid joining at 20:30. Lesson: sometimes the AI is right and the test is wrong |
| 5 | Trying to break it | An LLM could, in principle, message the asker or a made-up person | Server code ignores messages to unknown people and status changes for the asker. Automated tests prove it | 41 tests pass |
| 6 | Model failure / timeout | A crash would freeze the page | Errors become a clean "error" event and the run ends properly | Tested with a fake timeout |
| 7 | Selling | Sales are different from borrowing: the asker is the seller | Added a "Selling" section to the prompt: find interested buyers, relay counter-offers, never pressure, item goes to the buyer's door, payment on pickup | Asma's bike sold to Sulaiman for 150 SAR |
| 8 | Explaining itself | Viewers could see *who* the robot asked but not *why* | The robot now returns a 3-7 word reason for each person it picks ("has a car, up early"); the page shows it on the apartment and in a "Why these neighbors?" card, next to who was left in peace and who was asleep | Every decision is explained on screen |
| 9 | Scaling up to a city | One building can't show whether the idea scales, and real apartments hold families, not single people | Built NearMind City: 5 neighborhoods, 20 buildings, 200 families of 4-8 (1,182 people). Each building gets its own prompt; family members are part of each household's prompt. Tests check that no names repeat | In a generated building, a chef asked for a calculator for his daughter's exam; the robot asked 2 of 9 neighbors, and one offered to check her own daughter's school bag |

`[Add one or two rounds of your own: something you noticed, what you changed, what happened.]`

**Final results (the five recorded runs):**

| Request | Asker | Contacted | Outcome |
|---|---|---|---|
| Movie night, 19:30 | Sedra | Alwalid, Layla | Alwalid joins at 20:30 |
| Ladder, 13:00 | Osama | Sulaiman, Asma | Sulaiman's 6 ft ladder, picked up at 2A |
| USB-C charger, 00:30 | Anas | Sedra | Sedra lends hers |
| Selling a bike, 17:00 | Asma | Yousef, Sulaiman | Sulaiman buys it for 150 SAR |
| Jump-start, 06:00 | Noor | Asma, Hamza, Sulaiman | Hamza comes down with cables in 5 minutes |

### 7. Limitations and ethical considerations

- **Simulated neighbors.** The test building is AI people. Real people answer late, change their minds, or ignore
  messages. (The WhatsApp version handles some of this: if nobody answers within 15 minutes, it tells the asker.)
- **The agent can still be wrong.** It guesses who might have something from public facts, so it can miss the
  person who actually has it. It never claims someone has something until they say so.
- **Privacy.** Even "public facts" like sleep hours are personal. A real version must ask everyone what they're
  willing to share, and let them change it.
- **Trust and safety.** Lending to strangers can go wrong (damaged items, unsafe meetings). NearMind says plainly
  when an offer sounds unsafe and prefers the safer one, but it can't verify people.
- **Fairness and pressure.** The same helpful neighbor could get asked again and again. People may feel they can't
  say no to an AI. NearMind asks politely, never pressures, and thanks people who say no.
- **Unintended consequences.** If it worked too well, people might stop talking to each other directly, the
  opposite of the goal. The design keeps the human in charge: NearMind introduces people, then they meet at the door.
- **Cost and dependence** on a paid AI model and an internet connection.

### 8. Future development

- **Pilot with real neighbors** in one building, using the WhatsApp version (people opt in by messaging first).
- **Fairness:** remember who helped recently and spread requests out; give helpers "thank-you" points.
- **Arabic and English** in the same building, each person in their own language.
- **Learning with consent:** remember who usually helps with what, only if they agree, and let them delete it.
- **Building-manager controls:** verified residents only, and a way to report problems.
- **Beyond one building:** a mosque community, a school, a university dorm.

### 9. Conclusion

NearMind turns a general language model into a specialized agent with one job: connect a neighbor who needs
something with the one or two neighbors who can help, and leave everyone else in peace. It understands the request,
reasons about who is likely to have it and be awake, asks politely, checks vague answers, recommends the safest or
fastest offer, and lets the human decide. Through nine rounds of testing it learned to ask fewer people, respect
sleep, never invent offers, and actually close deals. Small favors are how neighbors become a community, and
NearMind makes asking for one easy.

### 10. References

`[Add every source you used, in APA style. Examples of the format:]`
- OpenAI. (2026). *API documentation: Structured outputs / JSON mode*. https://platform.openai.com/docs
- ReadyAI. (2026). *WAICY 2026 guidebook*. https://www.waicy.org
- AI4K12. (n.d.). *The 5 big ideas in AI*. https://ai4k12.org/resources/big-ideas-poster/
- Remotion. (2026). *Remotion documentation*. https://www.remotion.dev/docs
- `[Any articles about neighbors, sharing or loneliness you read for your motivation.]`

---

## Part 2: WAICY Day script (only if you're selected)

The guidebook describes WAICY Day as a **3-minute presentation, a 3-minute demo, then 4 minutes of Q&A** with
the judges, live online or with videos. Presentation & Communication is worth 10 points, and live attendance is
needed for Q&A credit. (The guidebook describes this format under the AI Showcase track; confirm the format for the
LLM track when the selected list comes out on 2 December.)

### Presentation (3 minutes, with slides)

| Time | Slide | What you say |
|---|---|---|
| 0:00-0:30 | Title: NearMind | "Hi, I'm Aws, I'm 13, from Al Safi International Language School in Saudi Arabia. My project is NearMind, an AI agent that helps neighbors help each other." |
| 0:30-1:00 | The problem | "In apartment buildings, people live a few meters apart but don't know each other. When you need a ladder or a charger, you buy one you'll use once, or spam a group chat, or go without." `[your story]` |
| 1:00-1:40 | The service: 5 steps | "You send NearMind one message. It understands what you need, picks the one to three neighbors most likely to help and awake, asks them in their own style, checks vague answers, recommends the best offer, and you decide." |
| 1:40-2:20 | How I built and tested it | "I built a building with ten AI neighbors, each with a private inventory the agent can't see. Then I tried to make it fail. One neighbor invented jumper cables he didn't have, so I changed the prompts and tested again." |
| 2:20-3:00 | Responsible by design | "It asks as few people as possible, respects sleep, keeps chats private, never invents offers, and the human always decides." |

### Demo (3 minutes, live or recorded)

Setup: open NearMind full screen, press `R`, rehearse once.

| Time | Do | Say |
|---|---|---|
| 0:00-0:10 | Press `P` | "This is the building. Ten neighbors, the robot on the roof." |
| 0:10-1:10 | Press `5` (jump-start) | "It's 6 AM. Noor's car battery is dead. The robot scans the building. It can't see what anyone owns, so it reasons about who's awake and might have a car. It asks three people. Yousef is asleep, so it leaves him alone. Hamza has cables. The robot recommends him, Noor chooses, and everyone else is thanked." |
| 1:10-1:25 | Point at the counter | "Three of nine contacted. Six left in peace. That's the number I care about." |
| 1:25-2:15 | `Esc`, then `4` (bike sale; `S` for 2× if short on time) | "It also works for selling. Asma wants 150 riyals for her bike. The robot finds the neighbors who'd want a bike and closes the deal with Sulaiman, at his door." |
| 2:15-2:45 | Type a new request live, e.g. "anyone have a sewing kit?" | "This one isn't recorded. Let's see who it asks." |
| 2:45-3:00 | Show the timeline | "Every step is visible: what the robot thinks, every message, every decision." |

If something goes wrong live: press `R`, then the demo number. The demos are recorded, so they always replay the same.

### Q&A practice questions

- Why not just send the request to everyone? *(It's rude and noisy; asking fewer people is the point.)*
- How does it know who has something? *(It doesn't. It reasons from public facts and has to ask, like a person would.)*
- What if it lies? *(Neighbors can only offer what they really own, the agent only relays what was said, and the
  code checks its actions.)*
- What about privacy? *(The agent never sees inventories; neighbors never see each other's chats.)*
- Is it real? *(The neighbors in the demo are simulated AI people. A WhatsApp version exists for real people, with
  strict safety rules, and a real pilot is the next step.)*
- What was the hardest bug? `[your answer]`
