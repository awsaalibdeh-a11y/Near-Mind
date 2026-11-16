# Two bugs seen in the okal "Live request" UI (temporal.nearmind), 2026-11-15

This code isn't on GitHub (`awsaalibdeh-a11y/Near-Mind` both branches stop at `be55165`), so please fix it in the okal workspace.

## 1. Bot timestamps are one hour behind the user's
Transcript order: user "K need a lader" **16:49** → NearMind reply **15:49**; user "accept alis" **16:51** → reply **15:51**.
Every reply is exactly 1h earlier than the message it answers. User messages and bot messages get their times from different
clocks or zones (for example the server's naive local time vs UTC, or the client's local time vs the server's). Fix: stamp every message
server-side as timezone-aware UTC (ISO 8601 with offset) and format it in the browser's local zone only at render time.
Test: a reply's timestamp is never earlier than the user message it answers.

## 2. "accept alis" did not confirm the ladder; it recommended a screwdriver
After the ladder offer from Ali ("Recommendation: accept it"), the user replied "accept alis". The next reply was a fresh recommendation
for Ali's screwdriver instead of confirming the ladder handover. So acceptance is matched to the wrong or a stale offer (or "accept"
isn't recognised and falls through to a new search), and the typo "alis" for "Ali's" isn't tolerated.
Fix: when there's an open recommendation, treat accept/yes/ok/"accept <name>" (fuzzy name match) as accepting *that* offer and move to
handover. Never start a new item search on an acceptance. Test: ladder request → Ali offer → "accept alis" ⇒ handover for the
**ladder** with Ali; no other item mentioned.

## Minor
Replies sound templated ("Ali is available and has a step ladder in good condition... Recommendation: accept it."). The style-matched
wording the product promises isn't coming through in this path.
