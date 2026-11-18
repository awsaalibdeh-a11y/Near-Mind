"""Build the WAICY 2026 submission PDF: waicy/LLM_Middle_NearMind.pdf (python tools/make_waicy_pdf.py).

The text follows WAICY.md Part 1 (the ten sections the guidebook asks for, in its order); screenshots are in waicy/img/.
"""
import os

from PIL import Image as PILImage
from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "waicy", "img")
OUT = os.path.join(ROOT, "waicy", "LLM_Middle_NearMind.pdf")
LIVE = "https://nearmind.awsaa-libdeh.workers.dev"
CHAT = LIVE + "/chat/jump"
CODE = "https://github.com/awsaalibdeh-a11y/Near-Mind"

F = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("UI", F + "segoeui.ttf"))
pdfmetrics.registerFont(TTFont("UI-B", F + "segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("UI-I", F + "segoeuii.ttf"))
pdfmetrics.registerFont(TTFont("UI-BI", F + "segoeuiz.ttf"))
pdfmetrics.registerFontFamily("UI", normal="UI", bold="UI-B", italic="UI-I", boldItalic="UI-BI")

INK, MUTED = colors.HexColor("#14232b"), colors.HexColor("#5b6b70")
ACC, ACC_BG, LINE = colors.HexColor("#0b8f69"), colors.HexColor("#e6f7f0"), colors.HexColor("#cfdcd7")
BLUE = colors.HexColor("#1d6fa3")

P = ParagraphStyle("p", fontName="UI", fontSize=10, leading=14.2, textColor=INK, spaceAfter=5)
SM = ParagraphStyle("sm", parent=P, fontSize=8.7, leading=11.6, spaceAfter=0)
CAP = ParagraphStyle("cap", parent=P, fontName="UI-I", fontSize=8.6, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceAfter=10)
H1 = ParagraphStyle("h1", parent=P, fontName="UI-B", fontSize=15, leading=19, textColor=ACC, spaceBefore=6, spaceAfter=6, keepWithNext=1)
H3 = ParagraphStyle("h3", parent=P, fontName="UI-B", fontSize=10.8, leading=14, spaceBefore=4, spaceAfter=3, keepWithNext=1)
TITLE = ParagraphStyle("t", parent=P, fontName="UI-B", fontSize=34, leading=40, alignment=TA_CENTER, spaceAfter=4)
SUB = ParagraphStyle("s", parent=P, fontSize=13, leading=18, alignment=TA_CENTER, textColor=MUTED, spaceAfter=14)
META = ParagraphStyle("m", parent=P, fontSize=10.5, leading=15.5, alignment=TA_CENTER)

W = A4[0] - 36 * mm  # text width


def link(url, text=None):
    return f'<a href="{url}" color="#1d6fa3"><u>{text or url}</u></a>'


def para(t, st=P):
    return Paragraph(t, st)


def bullets(items, st=P):
    return ListFlowable([ListItem(Paragraph(t, st), leftIndent=12, value="•") for t in items],
                        bulletType="bullet", start="•", leftIndent=12, bulletFontName="UI", bulletFontSize=9, spaceAfter=4)


def numbered(items):
    return ListFlowable([ListItem(Paragraph(t, P), leftIndent=14) for t in items],
                        bulletType="1", leftIndent=14, bulletFontName="UI-B", bulletFontSize=9.5, bulletColor=ACC)


def table(rows, widths, head=True):
    data = [[Paragraph(f"<b>{c}</b>" if head and i == 0 else c, SM) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * W for w in widths], repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if head:
        st.append(("BACKGROUND", (0, 0), (-1, 0), ACC_BG))
    t.setStyle(TableStyle(st))
    return t


def pic(name, caption, width=1.0, max_h=None):
    path = os.path.join(IMG, name)
    w0, h0 = PILImage.open(path).size
    w = W * width
    h = w * h0 / w0
    if max_h and h > max_h:
        h, w = max_h, max_h * w0 / h0
    im = Image(path, width=w, height=h)
    frame = Table([[im]], colWidths=[w + 2])
    frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 1),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 1), ("TOPPADDING", (0, 0), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return KeepTogether([frame, Spacer(1, 3), para(caption, CAP)])


def callout(t):
    box = Table([[Paragraph(t, P)]], colWidths=[W])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACC_BG), ("LINEBEFORE", (0, 0), (0, -1), 3, ACC),
                             ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                             ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return box


s = []

# ---------- cover ----------
s += [Spacer(1, 22 * mm), para("NearMind", TITLE),
      para("An AI agent that helps neighbors help each other", SUB),
      pic("city.jpg", "NearMind City: 5 neighborhoods, 20 buildings, 200 families, 1,182 people, one robot on every roof."),
      Spacer(1, 4 * mm),
      para("<b>WAICY 2026 · LLM &amp; AI Agent Track</b> (theme: <i>AI as a Service</i>)", META),
      para("Aws Alaa · Age 13 · Grade 8 · Al Safi International Language School · Saudi Arabia", META),
      Spacer(1, 5 * mm),
      table([["Live chatbot", link(LIVE)],
             ["Chat history (16 messages)", link(CHAT)],
             ["Source code", link(CODE) + " (branch <i>local-app-street</i>, folder <i>local-app/</i>)"]],
            [0.3, 0.7], head=False),
      PageBreak()]

# ---------- 1 ----------
s += [para("1. What specific service NearMind provides", H1),
      para("<b>NearMind is a neighborhood-sharing agent for one apartment building.</b> A resident sends one message, "
           "such as “Need a ladder to change a ceiling bulb”, “my phone is dying, anyone have a USB-C charger?” or "
           "“I'm selling my old bike for 150 SAR”. NearMind finds the one or two neighbors who can actually help, talks to "
           "them, and arranges the handover, without spamming the whole building."),
      para("It is deliberately narrow. It is not a general assistant, and not a marketplace. Each building has its own "
           "robot, which only connects the 10 families inside that building. To show it scales, the demo is a whole "
           "simulated city: <b>NearMind City, with 5 neighborhoods, 20 buildings, 200 families and 1,182 people</b> "
           "(4-8 per apartment: parents, sons, daughters, grandparents), with no name repeated anywhere. You tap a "
           "neighborhood on the city map, then a building, then an apartment. It handles four kinds of request:"),
      table([["Kind", "Example"],
             ["Borrow an item", "a ladder, a charger, jumper cables"],
             ["A small favor", "help with a dead car battery at 6 AM"],
             ["Company", "someone to watch a movie with tonight"],
             ["Sell something", "a bike for 150 SAR, delivered to the buyer's door"]], [0.3, 0.7]),
      Spacer(1, 6),
      para("<b>What it does, step by step</b> (this is written into its instructions):"),
      numbered([
          "<b>Understand</b> the request: item, quantity, urgency, sensible substitutes. If it's unclear, ask one short "
          "question first instead of guessing.",
          "<b>Choose who to ask:</b> 1-3 neighbors most likely to have it <b>and</b> be awake, using only public facts "
          "(job, hobbies, sleep hours) and the time of day. Two normally; three only when urgent. Never everyone.",
          "<b>Clarify</b> vague answers (“the long thing in the garage”) with that neighbor before reporting back.",
          "<b>Recommend</b> the best offer with a reason (fastest, safest, awake), and let the asker choose.",
          "<b>Hand over:</b> confirm time and place with the chosen neighbor, thank and release the others, and close."]),
      Spacer(1, 4),
      callout("<b>The value:</b> you get what you need in minutes instead of buying something you'll use once, and the "
              "rest of the building isn't disturbed. On screen, a counter shows it, for example "
              "“Neighbors contacted: 3 of 9 · 6 left in peace”."),
      para("<i>Why not just use WhatsApp? It's the most important question about NearMind, so it gets its own page at the end of this section.</i>", SM),
      Spacer(1, 8),
      pic("hood.jpg", "Tapping a neighborhood (Al Noor Gardens) shows its four buildings; each one works live.", 0.6),
      pic("building.jpg", "The Roof Robot Tower: ten families on five floors, the NearMind robot on the roof. "
                          "The side panel shows the asker's family and who can ask."),
      CondPageBreak(45 * mm),
      para("How it's built", H3),
      bullets([
          "<b>The agent (the robot on the roof)</b> is an LLM (<i>gpt-6.1-terra</i>, OpenAI JSON mode) with a detailed "
          "system prompt. Each turn it replies with one JSON object: a one-line “think” shown to the audience, what it "
          "understood (item, kind, price, urgency), which phase it's in, a status for each neighbor (asked, offer, no, "
          "chosen, released), <b>a short reason for each neighbor it picks</b> (shown on screen), the messages to send, "
          "and up to three quick-reply buttons for the asker.",
          "<b>200 simulated families</b> test it. In each building, every apartment's contact person is a separate LLM "
          "call with its own personality, job, sleep hours, budget, wish list, family members and a <b>private inventory "
          "the agent never sees</b>. So the agent has to reason and ask, like in real life, rather than look things up. "
          "Families help too: a neighbor may say their teenage son can carry it down.",
          "<b>The city is generated by code</b> (fixed seed) with strict rules checked by tests: every neighborhood and "
          "building name is different, no first name repeats inside a building, every family name is different, and no "
          "two people in the city share a full name. Each building gets its own robot prompt with its own 10 families.",
          "<b>Code checks the agent:</b> the server ignores any message to an unknown person (or someone from another "
          "building), never lets it mark the asker, and turns model errors into a clean message instead of a crash. "
          "45 automated tests check this with the model faked.",
          "<b>The website</b> turns each step into animation: every message flies between the apartments and the robot, "
          "and when a deal closes the item travels door to door. Portraits were illustrated with an AI image tool; the "
          "animation uses Remotion."]),
      ]


# ---------- the big question: its own page ----------
def ping_panel(title, sub, mode):
    """Noor at the top, her 9 neighbors below. mode 'group': everyone pinged; 'nm': only the 3 the robot chose."""
    pw, ph = W / 2 - 5 * mm, 72 * mm
    d = Drawing(pw, ph)
    good, bad, grey, sleep = colors.HexColor("#17b583"), colors.HexColor("#e5484d"), colors.HexColor("#c9d3d0"), colors.HexColor("#6c63c7")
    d.add(Rect(0, 0, pw, ph, rx=8, ry=8, fillColor=colors.HexColor("#f6faf8"), strokeColor=LINE, strokeWidth=0.8))
    d.add(String(pw / 2, ph - 15, title, fontName="UI-B", fontSize=12.5, fillColor=INK, textAnchor="middle"))
    d.add(String(pw / 2, ph - 27, sub, fontName="UI", fontSize=8.2, fillColor=MUTED, textAnchor="middle"))
    nx, ny = pw / 2, ph - 50
    # the jump-start at 6 AM: who's asleep, and who NearMind actually asked
    people = [("Sedra", 1, 0), ("Sulaiman", 0, 1), ("Asma", 0, 1), ("Hamza", 0, 1), ("Osama", 1, 0),
              ("Alwalid", 0, 0), ("Anas", 1, 0), ("Layla", 0, 0), ("Yousef", 1, 0)]
    cols, gap = 5, pw / 5.6
    pts = []
    for i, (name, asleep, asked) in enumerate(people):
        r, c = divmod(i, cols)
        n_in_row = cols if r == 0 else len(people) - cols
        x = pw / 2 + (c - (n_in_row - 1) / 2) * gap
        y = 52 - r * 32
        pts.append((x, y, name, asleep, asked))
    for x, y, name, asleep, asked in pts:
        hit = mode == "group" or asked
        if hit:
            d.add(Line(nx, ny - 9, x, y + 9, strokeColor=bad if mode == "group" else good, strokeWidth=1.1,
                       strokeDashArray=None if mode == "nm" else [2, 2]))
    for x, y, name, asleep, asked in pts:
        hit = mode == "group" or asked
        fill = (bad if (mode == "group" and asleep) else colors.HexColor("#f59e0b")) if mode == "group" else (good if asked else grey)
        d.add(Circle(x, y, 9, fillColor=fill, strokeColor=colors.white, strokeWidth=1.2))
        if mode == "nm" and asked:  # a drawn check mark
            d.add(PolyLine([x - 4, y, x - 1.2, y - 3, x + 4, y + 3.5], strokeColor=colors.white, strokeWidth=1.8))
        mark = "!" if (mode == "group" and asleep) else ("" if (mode == "nm" and asked) else ("z" if asleep else ""))
        if mark:
            d.add(String(x, y - 3.2, mark, fontName="UI-B", fontSize=9, fillColor=colors.white, textAnchor="middle"))
        d.add(String(x, y - 18, name, fontName="UI", fontSize=6.6, fillColor=INK if hit else MUTED, textAnchor="middle"))
    d.add(Circle(nx, ny, 10, fillColor=colors.HexColor("#ec4899"), strokeColor=colors.white, strokeWidth=1.2))
    d.add(String(nx, ny - 3.2, "N", fontName="UI-B", fontSize=9.5, fillColor=colors.white, textAnchor="middle"))
    d.add(String(nx + 14, ny - 3, "Noor, 06:00", fontName="UI-B", fontSize=7.4, fillColor=INK))
    return d


def stat(n, label, col):
    return [Paragraph(f'<font size="20" color="{col}"><b>{n}</b></font>', ParagraphStyle("n", parent=P, alignment=TA_CENTER, leading=24)),
            Paragraph(label, ParagraphStyle("l", parent=SM, alignment=TA_CENTER, textColor=MUTED))]


BIG = ParagraphStyle("big", parent=P, fontName="UI-B", fontSize=24, leading=29, textColor=INK, spaceAfter=4)
LEAD = ParagraphStyle("lead", parent=P, fontSize=11.2, leading=16, spaceAfter=8)
QUOTE = ParagraphStyle("q", parent=P, fontName="UI-B", fontSize=15, leading=20, alignment=TA_CENTER, textColor=ACC)

panels = Table([[ping_panel("WhatsApp group", "one message → all 9 neighbors, at 6 AM", "group"),
                 ping_panel("NearMind", "one message → only the 3 who can help", "nm")]],
               colWidths=[W / 2, W / 2])
panels.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
stats = Table([[stat("9 → 3", "people messaged<br/>(same request)", "#0b8f69"), stat("4 → 0", "people woken up<br/>at 6 AM", "#0b8f69"),
                stat("6", "neighbors left<br/>in peace", "#0b8f69"), stat("1,182", "people in NearMind City:<br/>nobody can text them all", "#1d6fa3")]],
              colWidths=[W / 4] * 4)
stats.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6faf8")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))

s += [PageBreak(),
      para("THE BIG QUESTION", ParagraphStyle("k", parent=SM, fontName="UI-B", textColor=ACC, spaceAfter=2)),
      para("Why not just use WhatsApp?", BIG),
      para("WhatsApp is great for talking to people you already know. But on a large scale, <b>you're not going to "
           "knock on every door, or text tens of neighbors you've never spoken to</b>, just to borrow a ladder. A building "
           "group chat pings everyone, at any hour, and most of them can't help. So in real life, people just don't ask. "
           "NearMind does the opposite: you send one message, and it asks <b>only</b> the few people who can help.", LEAD),
      panels,
      para("The same request, the 6 AM jump-start from the recorded demo. Left: a group chat reaches all nine neighbors and wakes "
           "the four who are asleep (red). Right: NearMind asked Sulaiman, Asma and Hamza, who were awake, and left everyone else alone.", CAP),
      stats,
      Spacer(1, 10),
      table([["", "WhatsApp group / knocking on doors", "NearMind"],
             ["Who gets the message", "Everyone in the group, or you knock door by door", "Only the 1-3 people most likely to have it and be awake"],
             ["Time of day", "Pings people at 2 AM too", "Skips people who are probably asleep unless it's urgent"],
             ["Finding the right person", "You guess, or wait and hope", "It reasons from public facts (job, hobbies, sleep hours) and asks"],
             ["Vague answers", "You chase them yourself", "It asks a follow-up question before telling you"],
             ["Awkwardness", "You ask strangers yourself", "It asks politely for you; you choose the offer"],
             ["Privacy", "Everyone sees your request and every reply", "Each neighbor's chat is private; only you see the offers"],
             ["Scale", "Impossible with 200 families", "Works the same in every building of a 200-family city"]],
            [0.22, 0.36, 0.42]),
      Spacer(1, 12),
      para("WhatsApp is the phone line.<br/>NearMind is the one who knows who to call.", QUOTE),
      Spacer(1, 4),
      para("NearMind can even run <i>inside</i> WhatsApp: its first version did, with real neighbors who opted in.",
           ParagraphStyle("c2", parent=SM, alignment=TA_CENTER, textColor=MUTED)),
      PageBreak()]

# ---------- 2 ----------
s += [para("2. Who the users are", H1),
      para("NearMind has to give different answers to different people. Four askers from the test building:"),
      table([["User", "Who they are", "What they need", "What NearMind must consider"],
             ["<b>Noor, 5A</b>", "Pastry chef, early shifts", "06:00, her car battery is dead: jumper cables, now",
              "<b>Urgent</b>, so asking 3 people is okay. Most neighbors are asleep: choose people who are awake and "
              "likely to have a car. Speed beats everything"],
             ["<b>Asma, 2B</b>", "Kind neighbor, first-aid kit, tea", "Sell her old bike for 150 SAR",
              "She's the <b>seller</b>, so the agent looks for a <b>buyer</b>. Choose people whose interests fit, check "
              "they're interested at the price, answer their questions, never pressure anyone. The bike goes to the "
              "buyer's door"],
             ["<b>Sedra, 1A</b>", "Loves movies", "Someone to watch a movie with tonight",
              "It's <b>company</b>, not an item. Choose people who are free and sociable in the evening; agree on a time "
              "and place, and respect that some neighbors have small kids"],
             ["<b>Osama, 1B</b>", "Kitchen basics, not a handyman", "A ladder to change a ceiling bulb",
              "A normal <b>borrow</b>. Ask 2 people at most; prefer the <b>safer</b> offer (a proper ladder over standing "
              "on a chair) and say why"]], [0.13, 0.2, 0.25, 0.42]),
      Spacer(1, 6),
      para("The <b>neighbors being asked</b> are users too, and they're different: Anas (19, student) sleeps until noon; "
           "Alwalid has young kids; Yousef and Hamza have cars; Layla is retired and home a lot. NearMind writes to each in "
           "their own style, skips people who are probably asleep unless it's urgent, and never shows one neighbor's chat "
           "to another. In the other 19 buildings the families are different again (a chef with three daughters, a "
           "nurse on night shifts, grandparents who are home all day), and the same robot adapts to each of them."),
      pic("other.jpg", "A generated building in another neighborhood (Cardamom Court, Old Souq Quarter): different "
                       "families, a different robot prompt, the same agent.", 0.86),
      ]

# ---------- 3 ----------
s += [para("3. Motivation", H1),
      para("The neighbors next to my house barely make small talk with us. When they do talk to us, it's usually an "
           "order or a complaint: “move your bike”, “why did you ring our bell?” We live a few meters apart, but it "
           "feels like we're strangers, and sometimes like we're on opposite sides."),
      para("I don't think my neighbors are bad people. I think nobody ever gives neighbors an easy, friendly reason to "
           "talk. The only time we speak is when something goes wrong, so every conversation starts with a problem. "
           "Ringing someone's bell to ask for a favor feels awkward, and if they're annoyed, it can make things worse. "
           "So people stop asking, and buy things they'll use once, or go without, even though the family next door "
           "probably has what they need."),
      para("I wanted to flip that around. What if the first thing your neighbor heard from you was not a complaint, but "
           "“can I borrow your ladder?”, or “I can help you with that”? NearMind does the awkward part: it works out who "
           "is likely to help and awake, and asks politely, only them. That's why its most important rule is to ask "
           "<b>as few people as possible</b> and to leave everyone else in peace. A helper that annoys the whole street "
           "would just make neighbors more hostile, which is exactly what I'm trying to fix."),
      para("I also wanted to learn how to build an <b>agent</b>, not just a chatbot: something that makes decisions, "
           "talks to several people, keeps track of what each one said, and finishes a real task. Small favors are how "
           "neighbors start to trust each other, and I hope one day my neighbors and I talk about more than bikes and "
           "doorbells."),
      ]

# ---------- 4 + 5 ----------
s += [para("4. Link to the chat history", H1),
      para(link(CHAT)),
      para("The <b>jump-start at 6 AM</b> run (16 messages). Noor asks; NearMind asks Sulaiman (“retired mechanic, awake "
           "early”), Hamza (“has a car, awake early”) and Asma (“keeps emergency supplies”), and not Yousef, who's "
           "asleep. Sulaiman and Asma don't have cables but offer other help; Hamza does. NearMind recommends Hamza and "
           "says why; Noor chooses and says where her car is parked; NearMind confirms the place with Hamza, thanks the "
           "other two, and closes the request. Four more full conversations: "
           + ", ".join(link(LIVE + "/chat/" + n, "/chat/" + n) for n in ("ladder", "charger", "sale", "movie")) + "."),
      pic("chat.jpg", "The chat-history page for the jump-start run.", 0.72, max_h=125 * mm),
      para("5. Link to the chatbot", H1),
      para(link(LIVE)),
      para("To keep it fair and affordable, each visitor gets their own private building, and there's a limit on live "
           "requests per hour and per day. The five recorded demos always work."),
      para("<b>How to use it:</b> tap a neighborhood, then a building, then an apartment to choose who's asking. Type a "
           "request or tap a preset, and watch it play out. Change the time of day and the sky changes and people go to "
           "sleep. <b>Watch a demo</b> (in The Roof Robot Tower) replays five recorded real runs instantly. Keyboard: "
           "<b>1</b>-<b>5</b> demos, <b>I</b> how it works, <b>P</b> full screen, <b>S</b> speed, <b>R</b> reset."),
      pic("demo.jpg", "The jump-start demo at 06:00: the robot has asked Hamza, Asma and Sulaiman, each with a reason "
                      "under their name. Four neighbors are asleep and left alone. The counter shows 3 of 9 contacted."),
      ]

# ---------- 6 ----------
s += [para("6. Iterative design process", H1),
      para("<b>Idea.</b> An agent that sits between neighbors: you ask once, it asks the right people. The first version "
           "ran on WhatsApp with real people, so it had strict safety rules from day one: it never starts a chat, never "
           "auto-replies in someone's private chat, holds messages during quiet hours (22:00-08:00), and anyone can send "
           "“stop”."),
      para("<b>Advisor design.</b>"),
      bullets([
          "<i>Problem:</i> you can't test an agent like this safely on real neighbors at 3 AM. <i>Decision:</i> build a "
          "simulated building where every neighbor is an AI person with a private inventory.",
          "<i>Problem:</i> if the agent could see everyone's inventory, it would just look it up. That's not realistic and "
          "not private. <i>Decision:</i> the agent only gets <b>public facts</b> (job, hobbies, sleep hours, apartment). "
          "Its prompt says “use only the PUBLIC facts and clock below, never guess inventories”.",
          "<i>Decision:</i> the agent answers in <b>strict JSON</b>, so the code can check every action, and the website "
          "can animate it.",
          "The building grew from 6 to <b>10 neighbors on 5 floors</b>, so that choosing who to ask became a real "
          "decision. Later it grew into a whole city of 200 families (round 9)."]),
      para("<b>Testing, error analysis and improvement.</b> Each round: run real requests, read every message, find what "
           "went wrong, change the prompt or the code, and run again."),
      table([["#", "What I tested", "What went wrong (error analysis)", "What I changed", "Result"],
             ["1", "Growing from 6 to 10 neighbors", "With more people to choose from, nothing stopped the agent from "
              "messaging lots of them, and nothing showed how many it bothered", "Prompt: “Pick the 1-3 neighbors... "
              "asking fewer people is better: never message everyone... Ask 2 normally; 3 only when urgent.” Added the "
              "on-screen <b>Neighbors contacted</b> counter to measure it", "In the five recorded demos it contacted 1-3 "
              "of 9 neighbors each time"],
             ["2", "Requests at night and early morning", "Waking people up is rude", "Each neighbor has sleep hours; the "
              "agent is told who is “probably ASLEEP” and “don't ping someone who is probably asleep unless it's urgent”. "
              "Sleeping neighbors reply sleepy and short", "At 06:00 the agent skipped Yousef (asleep)"],
             ["3", "6 AM jump-start", "<b>A simulated neighbor made something up:</b> Sulaiman offered jumper cables that "
              "weren't in his inventory. The agent would have relayed a false offer", "Neighbor prompt: “you ONLY own the "
              "things listed above; if something isn't listed, you don't have it”. Agent rule: “Only relay what neighbors "
              "actually said. Never invent that someone has something.”", "Re-ran: Sulaiman says no and offers to help "
              "push-start; Hamza, who really has cables, is chosen"],
             ["4", "Movie night", "The conversation never finished: the agent kept saying it would check and come back",
              "The agent was right to wait: it can't confirm a meeting without a time and place, and the test asker never "
              "gave one. The fix was in the test: the asker now proposes 20:30 at her flat", "Closes with Alwalid joining "
              "at 20:30. Lesson: sometimes the AI is right and the test is wrong"],
             ["5", "Trying to break it", "An LLM could, in principle, message the asker or a made-up person", "Server "
              "code ignores messages to unknown people and status changes for the asker. Automated tests prove it",
              "All tests pass"],
             ["6", "Model failure / timeout", "A crash would freeze the page", "Errors become a clean “error” event and "
              "the run ends properly", "Tested with a fake timeout"],
             ["7", "Selling", "Sales are different from borrowing: the asker is the seller", "Added a “Selling” section "
              "to the prompt: find interested buyers, relay counter-offers, never pressure, item goes to the buyer's "
              "door, payment on pickup", "Asma's bike sold to Sulaiman for 150 SAR"],
             ["8", "Explaining itself", "Viewers could see <i>who</i> the robot asked but not <i>why</i>", "The robot "
              "now returns a 3-7 word reason for each person it picks (“has a car, up early”), shown on the apartment "
              "and in a summary card, next to who was left in peace and who was asleep", "Every decision is explained "
              "on screen"],
             ["9", "Scaling up to a city", "One building can't show whether the idea scales, and real apartments hold "
              "families, not single people", "Built NearMind City: 5 neighborhoods, 20 buildings, 200 families of 4-8 "
              "(1,182 people). Each building gets its own prompt; family members are part of each household's prompt. "
              "Tests check that no names repeat", "In a generated building, a chef asked for a calculator for his "
              "daughter's exam; the robot asked 2 of 9 neighbors, and one offered to check her own daughter's school "
              "bag"]], [0.04, 0.15, 0.27, 0.32, 0.22]),
      Spacer(1, 8),
      KeepTogether([
          para("<b>Final results (the five recorded runs):</b>"),
          table([["Request", "Asker", "Contacted", "Outcome"],
                 ["Movie night, 19:30", "Sedra", "Alwalid, Layla", "Alwalid joins at 20:30"],
                 ["Ladder, 13:00", "Osama", "Sulaiman, Asma", "Sulaiman's 6 ft ladder, picked up at 2A"],
                 ["USB-C charger, 00:30", "Anas", "Sedra", "Sedra lends hers"],
                 ["Selling a bike, 17:00", "Asma", "Yousef, Sulaiman", "Sulaiman buys it for 150 SAR"],
                 ["Jump-start, 06:00", "Noor", "Asma, Hamza, Sulaiman", "Hamza comes down with cables in 5 minutes"]],
                [0.24, 0.12, 0.26, 0.38])]),
      Spacer(1, 10),
      ]

dec = Image(os.path.join(IMG, "decisions.jpg"), width=0.36 * W, height=0.36 * W * 1076 / 760)
dl_w = 0.6 * W
dl = Image(os.path.join(IMG, "delivered.jpg"), width=dl_w, height=dl_w * 1125 / 1800)
pair = Table([[dec, dl], [para("The robot's decisions after the jump-start run: who it asked and why, who it left in "
                               "peace, and the result.", CAP),
                          para("When a deal closes, the item travels door to door and the camera zooms in.", CAP)]],
             colWidths=[0.39 * W, 0.61 * W])
pair.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
s += [KeepTogether([pair])]

# ---------- 7-10 ----------
s += [para("7. Limitations and ethical considerations", H1),
      bullets([
          "<b>Simulated neighbors.</b> The test buildings are AI people. Real people answer late, change their minds, or "
          "ignore messages. (The WhatsApp version handles some of this: if nobody answers within 15 minutes, it tells "
          "the asker.)",
          "<b>The agent can still be wrong.</b> It guesses who might have something from public facts, so it can miss the "
          "person who actually has it. It never claims someone has something until they say so.",
          "<b>Privacy.</b> Even “public facts” like sleep hours are personal. A real version must ask everyone what "
          "they're willing to share, and let them change it.",
          "<b>Trust and safety.</b> Lending to strangers can go wrong (damaged items, unsafe meetings). NearMind says "
          "plainly when an offer sounds unsafe and prefers the safer one, but it can't verify people.",
          "<b>Fairness and pressure.</b> The same helpful neighbor could get asked again and again. People may feel they "
          "can't say no to an AI. NearMind asks politely, never pressures, and thanks people who say no.",
          "<b>Unintended consequences.</b> If it worked too well, people might stop talking to each other directly, the "
          "opposite of the goal. The design keeps the human in charge: NearMind introduces people, then they meet at "
          "the door.",
          "<b>Cost and dependence</b> on a paid AI model and an internet connection."]),
      para("8. Future development", H1),
      bullets([
          "<b>Pilot with real neighbors</b> in one building, using the WhatsApp version (people opt in by messaging first).",
          "<b>Fairness:</b> remember who helped recently and spread requests out; give helpers “thank-you” points.",
          "<b>Arabic and English</b> in the same building, each person in their own language.",
          "<b>Learning with consent:</b> remember who usually helps with what, only if they agree, and let them delete it.",
          "<b>Building-manager controls:</b> verified residents only, and a way to report problems.",
          "<b>Beyond one building:</b> a mosque community, a school, a university dorm."]),
      para("9. Conclusion", H1),
      para("NearMind turns a general language model into a specialized agent with one job: connect a neighbor who needs "
           "something with the one or two neighbors who can help, and leave everyone else in peace. It understands the "
           "request, reasons about who is likely to have it and be awake, asks politely, checks vague answers, recommends "
           "the safest or fastest offer, and lets the human decide. Through nine rounds of testing it learned to ask fewer "
           "people, respect sleep, never invent offers, explain its choices, and grow from one building to a city of "
           "1,182 people. Small favors are how neighbors become a community, and NearMind makes asking for one easy."),
      para("10. References", H1),
      para("AI4K12. (n.d.). <i>The 5 big ideas in AI</i>. " + link("https://ai4k12.org/resources/big-ideas-poster/")),
      para("OpenAI. (2026). <i>API documentation: Structured outputs and JSON mode</i>. " + link("https://platform.openai.com/docs")),
      para("Pallets. (2026). <i>Flask documentation</i>. " + link("https://flask.palletsprojects.com/")),
      para("ReadyAI. (2026). <i>WAICY 2026 guidebook</i>. " + link("https://www.waicy.org")),
      para("ReadyAI. (2026). <i>WAICY 2026 rubrics</i>. " + link("https://www.waicy.org/rubrics/")),
      para("Remotion. (2026). <i>Remotion documentation</i>. " + link("https://www.remotion.dev/docs")),
      ]


def deco(c, d):
    c.saveState()
    c.setFont("UI", 8)
    c.setFillColor(MUTED)
    if d.page > 1:
        c.drawString(18 * mm, 10 * mm, "NearMind · Aws Alaa · WAICY 2026 LLM & AI Agent Track")
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(d.page))
    c.setFillColor(ACC)
    c.rect(0, A4[1] - 4, A4[0], 4, stroke=0, fill=1)
    c.restoreState()


SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=17 * mm,
                  title="NearMind: WAICY 2026 LLM & AI Agent Track", author="Aws Alaa",
                  subject="LLM_Middle_NearMind").build(s, onFirstPage=deco, onLaterPages=deco)
print("wrote", OUT)
