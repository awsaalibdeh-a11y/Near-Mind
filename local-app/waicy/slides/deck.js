// NearMind WAICY 2026 deck. node deck.js <out.pptx>
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const React = require("react");
const RDS = require("react-dom/server");
const fa = require("react-icons/fa6");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const OUT = process.argv[2] || "NearMind_WAICY_2026.pptx";
const HERE = __dirname;
const REPO = "C:/Edits/nearmind";
const IMG = REPO + "/waicy/img/";
const LIVE = "https://nearmind.awsaa-libdeh.workers.dev";

const THEME = {
  name: "NearMind",
  headFontFace: "Segoe UI",
  bodyFontFace: "Segoe UI",
  colors: {
    dk1: "14232B", lt1: "FFFFFF", dk2: "0E2A2E", lt2: "EEF6F3",
    accent1: "0B8F69", accent2: "F59E0B", accent3: "EC4899", accent4: "1D6FA3", accent5: "E5484D", accent6: "6C63C7",
    hlink: "1D6FA3", folHlink: "6C63C7",
  },
};
const HEX = THEME.colors;

async function icon(Comp, color, size = 256) {
  const svg = RDS.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
async function portrait(name) {
  const out = path.join(HERE, "p_" + name + ".png");
  if (!fs.existsSync(out)) await sharp(REPO + "/static/img/" + name + ".webp").resize(400, 400).png().toFile(out);
  return out;
}
async function size(p) { const m = await sharp(p).metadata(); return [m.width, m.height]; }

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625
  pres.author = "Aws Alaa";
  pres.title = "NearMind: WAICY 2026 LLM & AI Agent Track";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  // ---------- layouts ----------
  pres.defineSlideMaster({
    title: "LIGHT",
    background: { path: path.join(HERE, "bg_map.png") },
    objects: [
      { rect: { x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.background1, transparency: 18 } } },
      { text: { text: "NearMind · Aws Alaa · WAICY 2026", options: { x: 0.5, y: 5.2, w: 5, h: 0.3, fontSize: 9, color: C.text2, margin: 0 } } },
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9, h: 0.75, fontSize: 28, bold: true, color: C.text1, margin: 0, valign: "middle" }, text: "" } },
    ],
    slideNumber: { x: 9.1, y: 5.2, w: 0.4, h: 0.3, fontSize: 9, color: C.text2, align: "right" },
  });
  pres.defineSlideMaster({ title: "PHOTO", background: { color: C.text1 }, objects: [] });

  const light = (sec, title) => { const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: sec }); s.addText(title, { placeholder: "title" }); return s; };
  const photo = (sec, bg) => { const s = pres.addSlide({ masterName: "PHOTO", sectionTitle: sec }); s.background = { path: path.join(HERE, bg) }; return s; };
  const panel = (s, x, y, w, h, t = 22) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.15, fill: { color: "0B1622", transparency: t }, line: { type: "none" }, objectName: "panel" });
  const card = (s, x, y, w, h, fill = C.background1) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: "D5E2DD", width: 0.75 },
    shadow: { type: "outer", color: "000000", opacity: 0.12, blur: 6, offset: 2, angle: 90 }, objectName: "card" });
  const kicker = (s, t, x, y, w, color = C.accent2) => s.addText(t, { x, y, w, h: 0.3, fontSize: 11, bold: true, color, charSpacing: 2, margin: 0, isTextBox: true });
  const iconDot = async (s, Comp, x, y, d, bg, fg = "FFFFFF") => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: bg }, line: { type: "none" }, objectName: "icon circle" });
    s.addImage({ data: await icon(Comp, fg), x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52, altText: "icon" });
  };

  // ---------- 1. title ----------
  pres.addSection({ title: "Intro" });
  let s = photo("Intro", "bg_title.png");
  panel(s, 0.45, 1.05, 5.0, 3.45, 30);
  kicker(s, "WAICY 2026 · LLM & AI AGENT TRACK", 0.8, 1.3, 4.5);
  s.addText("NearMind", { x: 0.8, y: 1.6, w: 4.5, h: 1.0, fontSize: 54, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addText("An AI agent that helps neighbors help each other", { x: 0.8, y: 2.6, w: 4.4, h: 0.8, fontSize: 19, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addText("Aws Alaa · 13 · Grade 8\nAl Safi International Language School · Saudi Arabia", { x: 0.8, y: 3.5, w: 4.5, h: 0.7, fontSize: 12, color: "D9E6F2", margin: 0, isTextBox: true });
  s.addNotes("Hi, I'm Aws, I'm 13, from Al Safi International Language School in Saudi Arabia. My project is NearMind, an AI agent that helps neighbors help each other. On every roof in this city there's a little robot, and its job is to connect neighbors.");

  // ---------- 2. problem ----------
  s = photo("Intro", "bg_hall.png");
  panel(s, 5.15, 0.5, 4.4, 4.6, 18);
  kicker(s, "WHY I BUILT THIS", 5.5, 0.8, 3.8);
  s.addText("Neighbors who only talk to complain", { x: 5.5, y: 1.1, w: 3.8, h: 0.9, fontSize: 24, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
  for (const [i, q] of ["“Move your bike.”", "“Why did you ring our bell?”"].entries()) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.5, y: 2.15 + i * 0.68, w: 3.6, h: 0.52, rectRadius: 0.12, fill: { color: "FFFFFF" }, line: { type: "none" }, objectName: "quote bubble" });
    s.addText(q, { x: 5.65, y: 2.15 + i * 0.68, w: 3.4, h: 0.52, fontSize: 15, italic: true, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  }
  s.addText("The neighbors next to my house barely make small talk. We live a few meters apart, but the only time we speak is when something goes wrong.",
    { x: 5.5, y: 3.6, w: 3.8, h: 1.2, fontSize: 13, color: "E6EEF5", margin: 0, isTextBox: true });
  s.addNotes("The neighbors next to my house barely make small talk with us. When they do talk, it's an order or a complaint: move your bike, why did you ring our bell. I don't think they're bad people. Nobody gives neighbors a friendly reason to talk, so every conversation starts with a problem. And ringing a bell to ask for a favor feels awkward, so people stop asking, and buy things they'll use once.");

  // ---------- 3. idea ----------
  pres.addSection({ title: "The service" });
  s = light("The service", "My idea: one message, the right neighbors");
  s.addText([
    { text: "You send NearMind one message.", options: { bold: true, breakLine: true } },
    { text: "It finds the 1-3 neighbors most likely to have it and be awake, asks only them, and arranges the handover. Everyone else is left in peace." },
  ], { x: 0.5, y: 1.35, w: 3.9, h: 2.4, fontSize: 17, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addText("Every building has its own robot. It only connects the 10 families inside it.", { x: 0.5, y: 3.9, w: 3.9, h: 0.8, fontSize: 13, italic: true, color: C.accent1, margin: 0, isTextBox: true });
  const kinds = [[fa.FaToolbox, "Borrow", "a ladder, a charger, jumper cables", C.accent1], [fa.FaCarBattery, "A favor", "help with a dead car battery at 6 AM", C.accent2],
    [fa.FaFilm, "Company", "someone to watch a movie with tonight", C.accent3], [fa.FaTag, "Sell", "a bike for 150 SAR, to the buyer's door", C.accent4]];
  for (const [i, [I, t, d, col]] of kinds.entries()) {
    const x = 4.75 + (i % 2) * 2.45, y = 1.3 + Math.floor(i / 2) * 1.85;
    card(s, x, y, 2.25, 1.65);
    await iconDot(s, I, x + 0.2, y + 0.2, 0.55, HEX[col] || col);
    s.addText(t, { x: x + 0.2, y: y + 0.82, w: 1.9, h: 0.32, fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
    s.addText(d, { x: x + 0.2, y: y + 1.12, w: 1.95, h: 0.45, fontSize: 11, color: C.text2, margin: 0, isTextBox: true });
  }
  s.addNotes("NearMind is deliberately narrow: not a general assistant, not a marketplace. It does one job: you send one message, and it finds the one to three neighbors who can actually help. It handles four kinds of request: borrowing, small favors, company, and selling.");

  // ---------- 4. five steps ----------
  s = light("The service", "How NearMind works: 5 steps");
  const steps = [[fa.FaMagnifyingGlass, "Understand", "Item, urgency, substitutes. Asks one question if it's unclear"],
    [fa.FaUserCheck, "Choose", "1-3 people likely to have it and be awake, from public facts only"],
    [fa.FaComments, "Clarify", "Checks vague answers before reporting back"],
    [fa.FaThumbsUp, "Recommend", "The best offer and why. You decide"],
    [fa.FaHandshake, "Hand over", "Time and place, thanks the others, closes"]];
  for (const [i, [I, t, d]] of steps.entries()) {
    const x = 0.5 + i * 1.84;
    card(s, x, 1.35, 1.66, 2.75);
    await iconDot(s, I, x + 0.53, 1.55, 0.6, HEX.accent1);
    s.addText(String(i + 1), { x: x + 0.1, y: 1.42, w: 0.4, h: 0.3, fontSize: 12, bold: true, color: C.accent2, margin: 0, isTextBox: true });
    s.addText(t, { x: x + 0.1, y: 2.3, w: 1.46, h: 0.35, fontSize: 15, bold: true, color: C.text1, align: "center", margin: 0, isTextBox: true });
    s.addText(d, { x: x + 0.12, y: 2.7, w: 1.42, h: 1.3, fontSize: 11, color: C.text2, align: "center", margin: 0, valign: "top", isTextBox: true });
    if (i < 4) s.addText("›", { x: x + 1.62, y: 2.45, w: 0.26, h: 0.4, fontSize: 22, bold: true, color: C.accent1, align: "center", margin: 0, isTextBox: true });
  }
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.2, y: 4.35, w: 5.6, h: 0.6, rectRadius: 0.3, fill: { color: C.background2 }, line: { color: HEX.accent1, width: 1 }, objectName: "counter pill" });
  s.addText([{ text: "Neighbors contacted: 3 of 9", options: { bold: true, color: C.accent1 } }, { text: "  ·  6 left in peace", options: { color: C.text2 } }],
    { x: 2.2, y: 4.35, w: 5.6, h: 0.6, fontSize: 15, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addNotes("These five steps are written into the robot's instructions. The counter at the bottom is the number I care most about: how many people it bothered, and how many it left in peace.");

  // ---------- 5. big question ----------
  pres.addSection({ title: "Why not WhatsApp" });
  s = photo("Why not WhatsApp", "bg_noise.png");
  panel(s, 0.45, 0.85, 5.3, 3.95, 12);
  kicker(s, "THE BIG QUESTION", 0.8, 1.15, 4.6);
  s.addText("Why not just use WhatsApp?", { x: 0.8, y: 1.45, w: 4.7, h: 1.0, fontSize: 30, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addText("On a large scale, you're not going to knock on every door, or text tens of neighbors you've never spoken to, just to borrow a ladder.",
    { x: 0.8, y: 2.55, w: 4.6, h: 1.15, fontSize: 16, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addText("A group chat pings everyone, at any hour, and most of them can't help. So in real life, people just don't ask.",
    { x: 0.8, y: 3.75, w: 4.6, h: 0.85, fontSize: 13, color: "E6EEF5", margin: 0, isTextBox: true });
  s.addNotes("This is the question I get the most. WhatsApp is great for people you already know. But on a large scale you're not going to knock on every door or text tens of people you've never spoken to. A group chat wakes everyone up, and most of them can't help.");

  // ---------- 6. same request, two ways ----------
  s = light("Why not WhatsApp", "Same request, two ways");
  const dg = path.join(HERE, "diagram.png"); const [dw, dh] = await size(dg);
  const DW = 6.3, DH = DW * dh / dw;
  s.addImage({ path: dg, x: (10 - DW) / 2, y: 1.15, w: DW, h: DH, altText: "Diagram: a WhatsApp group message reaches all 9 neighbors and wakes 4; NearMind asks only the 3 who can help" });
  const stats = [["9 → 3", "people messaged"], ["4 → 0", "people woken at 6 AM"], ["6", "neighbors left in peace"], ["1,182", "people in NearMind City"]];
  const sy = 1.15 + DH + 0.2;
  for (const [i, [n, l]] of stats.entries()) {
    const x = 0.9 + i * 2.1;
    card(s, x, sy, 1.95, 0.95);
    s.addText(n, { x, y: sy + 0.06, w: 1.95, h: 0.5, fontSize: 24, bold: true, color: i === 3 ? C.accent4 : C.accent1, align: "center", margin: 0, isTextBox: true });
    s.addText(l, { x, y: sy + 0.56, w: 1.95, h: 0.3, fontSize: 10.5, color: C.text2, align: "center", margin: 0, isTextBox: true });
  }
  s.addNotes("Here's the same request, the 6 AM jump-start from my demo. On the left, a group chat reaches all nine neighbors and wakes the four who are asleep. On the right, NearMind asked only Sulaiman, Asma and Hamza, who were awake. Nine messages became three, four people woken became zero.");

  // ---------- 7. comparison ----------
  s = light("Why not WhatsApp", "WhatsApp vs NearMind");
  const H = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.accent1 } } });
  const rows = [[H(""), H("WhatsApp group / knocking on doors"), H("NearMind")],
    ["Who gets the message", "Everyone, or you knock door by door", "Only the 1-3 most likely to help"],
    ["Time of day", "Pings people at 2 AM too", "Skips people who are asleep"],
    ["Finding the right person", "You guess, or wait and hope", "It reasons from public facts and asks"],
    ["Vague answers", "You chase them yourself", "It asks a follow-up question"],
    ["Awkwardness", "You ask strangers yourself", "It asks politely; you choose"],
    ["Privacy", "Everyone sees every reply", "Each chat is private"],
    ["Scale", "Impossible with 200 families", "Works in every building"]];
  s.addTable(rows.map((r, i) => r.map((c, j) => typeof c === "string" ? { text: c, options: { bold: j === 0, color: j === 2 ? HEX.accent1 : HEX.dk1, fill: { color: i % 2 ? "FFFFFF" : "F1F7F4" } } } : c)),
    { x: 0.5, y: 1.2, w: 9, colW: [2.3, 3.35, 3.35], fontSize: 12, fontFace: "Segoe UI", border: { type: "solid", color: "D5E2DD", pt: 0.75 }, rowH: 0.36, valign: "middle", margin: [0.04, 0.1, 0.04, 0.1] });
  s.addText([{ text: "WhatsApp is the phone line. ", options: { color: C.text1 } }, { text: "NearMind is the one who knows who to call.", options: { color: C.accent1 } }],
    { x: 0.5, y: 4.3, w: 9, h: 0.55, fontSize: 18, bold: true, align: "center", margin: 0, isTextBox: true });
  s.addNotes("And NearMind can even run inside WhatsApp; its first version did, with real neighbors who opted in. WhatsApp is the phone line. NearMind is the one who knows who to call.");

  // ---------- 8. scale ----------
  pres.addSection({ title: "How it's built" });
  s = light("How it's built", "Built to scale: NearMind City");
  const big = [["5", "neighborhoods"], ["20", "buildings"], ["200", "families"], ["1,182", "people"]];
  for (const [i, [n, l]] of big.entries()) {
    const x = 0.5 + (i % 2) * 1.85, y = 1.3 + Math.floor(i / 2) * 1.3;
    card(s, x, y, 1.7, 1.15);
    s.addText(n, { x, y: y + 0.1, w: 1.7, h: 0.6, fontSize: 30, bold: true, color: C.accent1, align: "center", margin: 0, isTextBox: true });
    s.addText(l, { x, y: y + 0.72, w: 1.7, h: 0.3, fontSize: 12, color: C.text2, align: "center", margin: 0, isTextBox: true });
  }
  s.addText("4-8 people in every apartment, no name repeated anywhere, a robot on every roof. Every building works live.", { x: 0.5, y: 3.95, w: 3.55, h: 0.9, fontSize: 12.5, color: C.text1, margin: 0, isTextBox: true });
  s.addImage({ path: IMG + "city.jpg", x: 4.35, y: 1.3, w: 5.15, h: 5.15 * 1125 / 1800, altText: "Screenshot of the NearMind City map", rounding: false });
  s.addNotes("To show the idea scales, I built a whole city by code: five neighborhoods, twenty buildings, two hundred families and 1,182 people. Tests check that no names repeat. Each building gets its own robot with its own families.");

  // ---------- 9. users ----------
  s = light("How it's built", "Different users, different answers");
  const users = [["noor", "Noor, 5A", "Jumper cables at 6 AM", "Urgent: ask up to 3, only people who are awake"],
    ["asma", "Asma, 2B", "Sell her bike for 150 SAR", "She's the seller: find a buyer, never pressure"],
    ["sedra", "Sedra, 1A", "A movie buddy tonight", "Company, not an item: who's free this evening?"],
    ["osama", "Osama, 1B", "A ladder for a ceiling bulb", "Normal borrow: ask 2, prefer the safer offer"]];
  for (const [i, [img, n, need, think]] of users.entries()) {
    const x = 0.5 + i * 2.3;
    card(s, x, 1.3, 2.1, 3.0);
    s.addImage({ path: await portrait(img), x: x + 0.55, y: 1.5, w: 1.0, h: 1.0, rounding: true, altText: n + " portrait" });
    s.addText(n, { x: x + 0.1, y: 2.6, w: 1.9, h: 0.35, fontSize: 15, bold: true, color: C.text1, align: "center", margin: 0, isTextBox: true });
    s.addText(need, { x: x + 0.15, y: 2.98, w: 1.8, h: 0.55, fontSize: 12, bold: true, color: C.accent1, align: "center", margin: 0, isTextBox: true });
    s.addText(think, { x: x + 0.15, y: 3.6, w: 1.8, h: 1.1, fontSize: 11, color: C.text2, align: "center", margin: 0, valign: "top", isTextBox: true });
  }
  s.addNotes("NearMind has to give different answers to different people. Noor's request is urgent, so asking three people is fine. Asma is selling, so the robot looks for a buyer. Sedra wants company, not an item. Osama needs a ladder, and the robot prefers the safer offer.");

  // ---------- 10. how it's built ----------
  s = photo("How it's built", "bg_robot.png");
  panel(s, 4.85, 0.45, 4.7, 4.75, 15);
  s.addText("How it's built", { x: 5.2, y: 0.65, w: 4.1, h: 0.6, fontSize: 26, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
  const built = [[fa.FaRobot, "The robot", "An LLM (gpt-6.1-terra) that replies in strict JSON, with a reason for every neighbor it picks"],
    [fa.FaLock, "200 simulated families", "Each with a private inventory the robot never sees, so it has to ask"],
    [fa.FaShieldHalved, "Code checks the AI", "No messages to unknown people, clean errors, 45 automated tests"],
    [fa.FaWandMagicSparkles, "Every message animated", "Built with Remotion; portraits made with an AI image tool"]];
  for (const [i, [I, t, d]] of built.entries()) {
    const y = 1.4 + i * 0.92;
    await iconDot(s, I, 5.2, y, 0.55, HEX.accent1);
    s.addText(t, { x: 5.9, y: y - 0.04, w: 3.4, h: 0.3, fontSize: 14, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
    s.addText(d, { x: 5.9, y: y + 0.26, w: 3.45, h: 0.55, fontSize: 11, color: "D9E6F2", margin: 0, isTextBox: true });
  }
  s.addNotes("The robot is a language model that answers in strict JSON, so my code can check every action. Each neighbor is a separate AI person with a private inventory the robot can't see, so it has to reason and ask, like in real life. And 45 automated tests check the rules.");

  // ---------- 11. demo ----------
  pres.addSection({ title: "Testing" });
  s = light("Testing", "Demo: jump-start at 6 AM");
  s.addImage({ path: IMG + "demo.jpg", x: 0.5, y: 1.2, w: 5.8, h: 5.8 * 1125 / 1800, altText: "Screenshot of the jump-start demo" });
  const DH2 = 3.625, DW2 = DH2 * 760 / 1076;
  s.addImage({ path: IMG + "decisions.jpg", x: 9.5 - DW2, y: 1.2, w: DW2, h: DH2, altText: "The robot's decisions: asked Sulaiman, Asma and Hamza; 6 left in peace" });
  s.addText("Noor's battery is dead. The robot asks 3 awake neighbors, leaves the 4 who are asleep alone, and Hamza brings his cables.",
    { x: 0.5, y: 4.88, w: 9, h: 0.28, fontSize: 10.5, italic: true, color: C.text2, margin: 0, isTextBox: true });
  s.addNotes("It's 6 AM. Noor's car battery is dead. The robot can't see what anyone owns, so it reasons about who's awake and might have a car. It asks three people and leaves Yousef, who's asleep, alone. Hamza has cables. The robot recommends him, Noor chooses, and everyone else is thanked. Three of nine contacted, six left in peace.");

  // ---------- 12. iterations ----------
  s = light("Testing", "Iterative design: 9 rounds of testing");
  const its = [["Ask fewer people", "1-3 of 9 contacted"], ["Respect sleep", "skipped Yousef at 06:00"], ["No made-up offers", "only relays what was said"],
    ["Movie night got stuck", "the test was wrong, not the AI"], ["Trying to break it", "server blocks bad messages"], ["Model failure", "a clean error, no freeze"],
    ["Selling", "bike sold for 150 SAR"], ["Explaining itself", "a reason for every pick"], ["Scaling up", "200 families, 1,182 people"]];
  for (const [i, [t, r]] of its.entries()) {
    const x = 0.5 + (i % 3) * 3.05, y = 1.2 + Math.floor(i / 3) * 1.25;
    card(s, x, y, 2.9, 1.1, i === 2 ? "FFF4E5" : C.background1);
    s.addShape(pres.shapes.OVAL, { x: x + 0.15, y: y + 0.28, w: 0.55, h: 0.55, fill: { color: i === 2 ? C.accent2 : C.accent1 }, line: { type: "none" }, objectName: "round number" });
    s.addText(String(i + 1), { x: x + 0.15, y: y + 0.28, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(t, { x: x + 0.85, y: y + 0.2, w: 1.95, h: 0.35, fontSize: 13, bold: true, color: C.text1, margin: 0, isTextBox: true });
    s.addText(r, { x: x + 0.85, y: y + 0.56, w: 1.95, h: 0.4, fontSize: 11, color: C.text2, margin: 0, isTextBox: true });
  }
  s.addNotes("Each round: I ran real requests, read every message, found what went wrong, changed the prompt or the code, and ran again. Round three, in orange, was the biggest bug. Next slide.");

  // ---------- 13. biggest bug ----------
  s = light("Testing", "Biggest bug: an AI neighbor made something up");
  s.addImage({ path: await portrait("sulaiman"), x: 0.5, y: 1.4, w: 1.3, h: 1.3, rounding: true, altText: "Sulaiman portrait" });
  s.addText("Sulaiman, 2A\nretired mechanic", { x: 0.35, y: 2.8, w: 1.6, h: 0.6, fontSize: 11, color: C.text2, align: "center", margin: 0, isTextBox: true });
  card(s, 2.2, 1.3, 3.2, 2.7, "FDECEC");
  s.addText("BEFORE", { x: 2.45, y: 1.45, w: 2.8, h: 0.3, fontSize: 12, bold: true, color: C.accent5, charSpacing: 2, margin: 0, isTextBox: true });
  s.addText("Sulaiman offered jumper cables that weren't in his inventory. NearMind would have passed a false offer to Noor.",
    { x: 2.45, y: 1.85, w: 2.75, h: 2.3, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addText("→", { x: 5.4, y: 2.45, w: 0.6, h: 0.6, fontSize: 30, bold: true, color: C.accent1, align: "center", margin: 0, isTextBox: true });
  card(s, 6.0, 1.3, 3.5, 2.7, "E6F7F0");
  s.addText("AFTER", { x: 6.25, y: 1.45, w: 3, h: 0.3, fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, margin: 0, isTextBox: true });
  s.addText("Neighbors only own what's on their private list, and the robot only relays what was actually said. Now Sulaiman offers to help push-start, and Hamza, who really has cables, is chosen.",
    { x: 6.25, y: 1.85, w: 3.05, h: 2.4, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addText("Lesson: test your AI by trying to make it fail.", { x: 0.5, y: 4.3, w: 9, h: 0.45, fontSize: 16, bold: true, italic: true, color: C.accent1, align: "center", margin: 0, isTextBox: true });
  s.addNotes("This was the hardest bug. A simulated neighbor, Sulaiman, offered jumper cables he didn't have. The robot would have told Noor a false offer. I changed both prompts: neighbors only own what's on their list, and the robot only relays what was actually said. I re-ran it, and Hamza, who really has cables, was chosen.");

  // ---------- 14. results ----------
  s = light("Testing", "Results: five recorded runs");
  const res = [["Request", "Asker", "Contacted", "Outcome"],
    ["Movie night, 19:30", "Sedra", "Alwalid, Layla", "Alwalid joins at 20:30"],
    ["Ladder, 13:00", "Osama", "Sulaiman, Asma", "Sulaiman's ladder, picked up at 2A"],
    ["Charger, 00:30", "Anas", "Sedra", "Sedra lends hers"],
    ["Selling a bike, 17:00", "Asma", "Yousef, Sulaiman", "Sulaiman buys it for 150 SAR"],
    ["Jump-start, 06:00", "Noor", "Asma, Hamza, Sulaiman", "Hamza brings cables in 5 min"]];
  s.addTable(res.map((r, i) => r.map((c) => ({ text: c, options: i === 0 ? { bold: true, color: "FFFFFF", fill: { color: HEX.accent1 } } : { color: HEX.dk1, fill: { color: i % 2 ? "FFFFFF" : "F1F7F4" } } }))),
    { x: 0.5, y: 1.25, w: 6.4, colW: [1.6, 0.8, 1.75, 2.25], fontSize: 11, fontFace: "Segoe UI", border: { type: "solid", color: "D5E2DD", pt: 0.75 }, rowH: 0.5, valign: "middle", margin: [0.04, 0.08, 0.04, 0.08] });
  card(s, 7.2, 1.25, 2.3, 1.45);
  s.addText("1-3 of 9", { x: 7.2, y: 1.35, w: 2.3, h: 0.7, fontSize: 30, bold: true, color: C.accent1, align: "center", margin: 0, isTextBox: true });
  s.addText("neighbors contacted per request", { x: 7.3, y: 2.05, w: 2.1, h: 0.5, fontSize: 11, color: C.text2, align: "center", margin: 0, isTextBox: true });
  card(s, 7.2, 2.95, 2.3, 1.45);
  s.addText("5 / 5", { x: 7.2, y: 3.05, w: 2.3, h: 0.7, fontSize: 30, bold: true, color: C.accent4, align: "center", margin: 0, isTextBox: true });
  s.addText("requests closed with a handover", { x: 7.3, y: 3.75, w: 2.1, h: 0.5, fontSize: 11, color: C.text2, align: "center", margin: 0, isTextBox: true });
  s.addNotes("These are the five recorded runs. Every one closed with a handover, and the robot never contacted more than three of the nine neighbors.");

  // ---------- 15. responsible + limits ----------
  pres.addSection({ title: "Wrap-up" });
  s = light("Wrap-up", "Responsible by design, and its limits");
  const good = ["Asks as few people as possible", "Leaves sleeping neighbors alone", "Keeps every chat private", "Never invents offers", "The human always decides"];
  const lim = ["Neighbors here are simulated AI people", "It can guess the wrong person", "Even sleep hours are personal data", "It can't verify people are safe", "People might stop talking directly"];
  for (const [col, list, I, hex, head] of [[0, good, fa.FaCircleCheck, HEX.accent1, "What it does"], [1, lim, fa.FaTriangleExclamation, HEX.accent2, "Limitations"]]) {
    const x = 0.5 + col * 4.6;
    card(s, x, 1.25, 4.4, 3.7);
    s.addText(head, { x: x + 0.3, y: 1.4, w: 3.8, h: 0.4, fontSize: 17, bold: true, color: col ? C.accent2 : C.accent1, margin: 0, isTextBox: true });
    const ic = await icon(I, hex);
    for (const [k, t] of list.entries()) {
      const y = 1.95 + k * 0.58;
      s.addImage({ data: ic, x: x + 0.3, y: y + 0.04, w: 0.28, h: 0.28, altText: "icon" });
      s.addText(t, { x: x + 0.72, y, w: 3.5, h: 0.38, fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
    }
  }
  s.addNotes("Responsible by design: it asks as few people as possible, respects sleep, keeps chats private, never invents offers, and the human always decides. But it has limits: the test neighbors are simulated, it can guess wrong, and even public facts like sleep hours are personal. A real version must ask people what they're willing to share.");

  // ---------- 16. future ----------
  s = light("Wrap-up", "What's next");
  const fut = [[fa.FaUsers, "Pilot with real neighbors", "using the WhatsApp version, opt-in only"], [fa.FaScaleBalanced, "Fairness", "spread requests out, thank-you points"],
    [fa.FaLanguage, "Arabic and English", "each person in their own language"], [fa.FaUserShield, "Learning with consent", "remember who helps, only if they agree"],
    [fa.FaBuilding, "Manager controls", "verified residents, report problems"], [fa.FaMosque, "Beyond buildings", "a mosque community, a school, a dorm"]];
  for (const [i, [I, t, d]] of fut.entries()) {
    const x = 0.5 + (i % 3) * 3.05, y = 1.3 + Math.floor(i / 3) * 1.8;
    card(s, x, y, 2.9, 1.6);
    await iconDot(s, I, x + 0.2, y + 0.22, 0.6, [HEX.accent1, HEX.accent4, HEX.accent6][i % 3]);
    s.addText(t, { x: x + 0.95, y: y + 0.22, w: 1.85, h: 0.6, fontSize: 14, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
    s.addText(d, { x: x + 0.2, y: y + 0.95, w: 2.55, h: 0.55, fontSize: 11.5, color: C.text2, margin: 0, isTextBox: true });
  }
  s.addNotes("Next, I want to pilot it with real neighbors in one building, add fairness so the same helper isn't asked every time, support Arabic and English together, and take it beyond buildings: a mosque community, a school, a dorm.");

  // ---------- 17. conclusion ----------
  s = photo("Wrap-up", "bg_door.png");
  panel(s, 0.4, 0.55, 4.6, 4.5, 15);
  s.addText("Small favors are how neighbors start to trust each other.", { x: 0.75, y: 0.85, w: 4.0, h: 1.5, fontSize: 24, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addText("NearMind makes asking for one easy.", { x: 0.75, y: 2.35, w: 4.0, h: 0.4, fontSize: 15, italic: true, color: "FCD34D", margin: 0, isTextBox: true });
  const links = [["Try it", LIVE, "nearmind.awsaa-libdeh.workers.dev"], ["Chat history", LIVE + "/chat/jump", "…workers.dev/chat/jump"], ["Code", "https://github.com/awsaalibdeh-a11y/Near-Mind", "github.com/awsaalibdeh-a11y/Near-Mind"]];
  for (const [i, [l, u, t]] of links.entries()) {
    s.addText([{ text: l + ":  ", options: { bold: true, color: "FFFFFF" } }, { text: t, options: { color: "9FE3C8", hyperlink: { url: u } } }],
      { x: 0.75, y: 3.0 + i * 0.4, w: 4.1, h: 0.35, fontSize: 12, margin: 0, isTextBox: true });
  }
  s.addText("Thank you!", { x: 0.75, y: 4.3, w: 4.0, h: 0.5, fontSize: 20, bold: true, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addNotes("NearMind turns a general language model into an agent with one job: connect a neighbor who needs something with the one or two who can help, and leave everyone else in peace. I hope one day my neighbors and I talk about more than bikes and doorbells. Thank you! You can try it yourself at the link.");

  // ---------- 18. references ----------
  s = light("Wrap-up", "References");
  const refs = ["AI4K12. (n.d.). The 5 big ideas in AI. https://ai4k12.org/resources/big-ideas-poster/",
    "OpenAI. (2026). API documentation: Structured outputs and JSON mode. https://platform.openai.com/docs",
    "Pallets. (2026). Flask documentation. https://flask.palletsprojects.com/",
    "ReadyAI. (2026). WAICY 2026 guidebook. https://www.waicy.org",
    "ReadyAI. (2026). WAICY 2026 rubrics. https://www.waicy.org/rubrics/",
    "Remotion. (2026). Remotion documentation. https://www.remotion.dev/docs"];
  card(s, 0.5, 1.25, 9, 3.0);
  await iconDot(s, fa.FaBookOpen, 0.8, 1.5, 0.6, HEX.accent1);
  s.addText(refs.map((r, i) => ({ text: r, options: { breakLine: i < refs.length - 1, paraSpaceAfter: 8 } })),
    { x: 1.65, y: 1.5, w: 7.6, h: 3.2, fontSize: 12.5, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("References in APA style.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
