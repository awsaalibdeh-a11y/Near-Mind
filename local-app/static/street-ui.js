// NearMind Street page: controls, live timeline and pacing. The scene itself is window.NMStreet (Remotion).
(() => {
"use strict";
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let P = {}, ORDER = [], asker = "sedra", clock = "", busy = false, speed = 1, mode = "ask", demo = false;
let REQ = null, CHOSEN = null, CLOSED = false;            // what this request is, who was chosen, whether it closed
let BID = null, BMETA = null, CITY = null, VIEW = "city";   // where you are in the city
let LEDGER = {};                                         // who has helped in this building so far (fairness)
let WHY = {}, ST = {}, MSGS = 0, ROUNDS = 0, SEEN = new Set(), DEMO_ID = null, T0 = 0;   // the AI-decision card and the result
const SID = (() => {                                        // one private street per browser tab on the public site
  const make = () => (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now()).replace(/-/g, "").slice(0, 32);
  try{ let s = sessionStorage.getItem("nm.sid"); if(!s){ s = make(); sessionStorage.setItem("nm.sid", s); } return s; }catch(e){ return make(); }
})();
const ICONS = [["ladder","🪜"],["stool","🪜"],["sugar","🍬"],["salt","🧂"],["egg","🥚"],["flour","🌾"],["milk","🥛"],["hammer","🔨"],["screwdriver","🪛"],
  ["drill","🔧"],["wrench","🔧"],["cord","🔌"],["extension","🔌"],["tape","🩹"],["umbrella","☔"],["charger","🔋"],["power bank","🔋"],["first aid","🩹"],
  ["plaster","🩹"],["jumper","🔋"],["cable","🔌"],["sewing","🧵"],["tent","⛺"],["pump","🚲"],["mixer","🧁"],["cake","🍰"],["flashlight","🔦"],["torch","🔦"],["candle","🕯️"],["movie","🎬"],["film","🎬"],["board game","🎲"],["game","🎮"],["controller","🎮"],
  ["bike","🚲"],["lamp","💡"],["fryer","🍳"],["pan","🍳"],["chair","🪑"],["monitor","🖥️"],["pot","🍲"],["plant","🪴"],["book","📚"]];
const iconFor = t => { t = String(t || "").toLowerCase(); const hit = ICONS.find(([k]) => t.includes(k)); return hit ? hit[1] : (REQ && REQ.kind === "company" ? "🤝" : "📦"); };

const PRESETS = [
  ["Pantry", [["🧂","Salt","Do you have a bit of salt? I'm in the middle of cooking"],["🍬","Sugar","Can I borrow a cup of sugar?"],["🥚","Eggs","Could I borrow 2 eggs for a cake?"],["🌾","Flour","Anyone have some flour? Baking tonight"],["🥛","Milk","Need a splash of milk for my coffee"]]],
  ["Tools", [["🔨","Hammer","Can I borrow a hammer to hang a picture?"],["🪛","Screwdriver","Need a screwdriver for 10 min"],["🔧","Drill","Does anyone have a drill? Putting up a shelf"],["🪜","Ladder","Need a ladder to change a ceiling bulb"]]],
  ["Handy", [["🔌","Extension cord","Anyone have an extension cord?"],["☔","Umbrella","It's pouring, can I borrow an umbrella?"],["🔋","Charger","My phone is dying, anyone have a USB-C charger?"],["🩹","First aid","I cut my finger, does anyone have plasters?"],["🔦","Flashlight","Power's out here, anyone have a flashlight or candles?"]]],
  ["Company", [["🎬","Movie buddy","I need someone to watch a movie with me tonight"],["🎲","Board games","Anyone up for board games this evening?"]]],
  ["عربي", [["🪜","سلم","أحتاج سلم صغير لتغيير لمبة في المطبخ، هل عند أحد؟"],["🍬","سكر","ممكن أستلف كوب سكر؟"],["🔋","شاحن","جوالي بيطفي، أحد عنده شاحن تايب سي؟"]]],
  ["Sell", [["🚲","Sell bike","I'm selling my old bike for 150 SAR"],["💡","Sell lamp","Selling a desk lamp, 40 SAR"],["🎮","Sell controller","Selling a spare game controller for 60 SAR"],["🍳","Sell air fryer","Selling an air fryer, barely used, 120 SAR"]]],
];

// ---------- pacing: events arrive in bursts; play them one at a time so every hop is visible ----------
const Q = []; let playing = false;
const wait = ms => new Promise(r => setTimeout(r, ms));
function enqueue(e){ Q.push(e); if(!playing) pump(); }
async function pump(){
  playing = true;
  while(Q.length){
    const e = Q.shift();
    show(e);
    await wait(delay(e));
  }
  playing = false;
}
function delay(e){
  const travel = (NMStreet.D / NMStreet.FPS) * 1000;
  if(e.t === "say") return Math.max(travel + 150, Math.max(1500, travel + 400 + Math.min(2200, e.text.length * 22)) / speed);
  if(e.t === "think") return 1300 / speed;
  if(e.t === "parse") return 500 / speed;
  if(e.t === "done") return 0;
  return 120 / speed;
}

// ---------- rendering one event: scene + timeline ----------
const name = id => id === "robot" ? "NearMind" : (P[id] || {}).name || id;
const color = id => id === "robot" ? "#17c394" : (P[id] || {}).color || "#9aa7b1";
const PHASE = {understand:"Understanding the request",outreach:"Asking neighbors",clarify:"Clarifying a reply",relay:"Reporting back",handover:"Arranging the handover",closed:"Done ✓"};
const STATE = {asked:"was asked",offer:"can help",no:"can't help",chosen:"was chosen ✓",released:"was thanked and released"};

function logRow(cls, icon, bg, html){
  const ol = $("#log"); const em = ol.querySelector(".empty"); if(em) em.remove();
  const li = document.createElement("li"); li.className = cls;
  const t = new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
  li.innerHTML = `<span class="ic" style="background:${bg}">${icon}</span><span class="tx">${html}<span class="meta">${t}</span></span>`;
  ol.appendChild(li); ol.scrollTop = ol.scrollHeight;
}

function show(e){
  switch(e.t){
    case "say":
      NMStreet.say(e.from, e.to, e.text);
      MSGS++;
      logRow("say", face(e.from), color(e.from),
        `<b>${esc(name(e.from))}</b> → <b>${esc(name(e.to))}</b><span class="q" dir="auto">${esc(e.text)}</span>`);
      break;
    case "think":
      NMStreet.think(e.text);
      ROUNDS++;
      logRow("think", "💭", "#d9f6ec", esc(e.text));
      break;
    case "parse":
      REQ = {item:e.item, kind:e.kind, price:e.price || ""};
      NMStreet.request({item:e.item, kind:e.kind, urgency:e.urgency, qty:e.qty, price:e.price || ""});
      logRow("parse", "📋", "#e2f1ff", `Understood: <b>${esc(e.item)}</b>${e.qty ? " · " + esc(e.qty) : ""}${e.urgency ? " · " + esc(e.urgency) + " urgency" : ""}`);
      break;
    case "status": {
      NMStreet.status(e.who, e.state);
      if(e.state === "chosen") CHOSEN = e.who;
      const sale = REQ && REQ.kind === "sale", txt = sale && e.state === "offer" ? "wants to buy it" : sale && e.state === "chosen" ? "is the buyer ✓" : STATE[e.state];
      if(txt && e.state !== "asked") logRow("status", face(e.who), color(e.who), `<b>${esc(name(e.who))}</b> ${txt}`);
      ST[e.who] = e.state; drawBrain();
    }
      break;
    case "why":
      NMStreet.why(e.who, e.text); WHY[e.who] = e.text; drawBrain();
      break;
    case "typing":
      NMStreet.typing(e.who, e.on);
      break;
    case "phase":
      if(e.phase === "closed") CLOSED = true;
      $("#phase").textContent = PHASE[e.phase] || e.phase;
      drawPipe(e.phase);
      break;
    case "quick":
      if(demo) break;
      $("#quick").innerHTML = e.options.map(o => `<button type="button">${esc(o)}</button>`).join("");
      break;
    case "ledger":
      LEDGER = e.helped || {}; drawHelpers();
      break;
    case "error":
      logRow("err", "⚠️", "#ffe2dc", esc(e.error));
      break;
    case "done":
      if(CLOSED && CHOSEN) finale();
      setBusy(false); demo = false;
      break;
  }
}

function finale(){
  const sale = REQ && REQ.kind === "sale", item = (REQ && REQ.item) || "your request";
  const from = sale ? asker : CHOSEN, to = sale ? CHOSEN : asker;
  NMStreet.finale({from, to, icon:iconFor(item), sale, label:item.charAt(0).toUpperCase() + item.slice(1),
    note: sale ? `${name(from)} → ${name(to)}${REQ.price ? " · " + REQ.price : ""}` : `from ${name(from)} · at ${name(to)}'s door`});
  logRow("done", "🎉", "#d9f6ec", `<b>${sale ? "Sold" : "Done"}:</b> ${esc(item)} ${sale ? "goes to" : "arrives at"} <b>${esc(name(to))}</b>'s door`);
  drawResult({sale, item, from, to});
  CLOSED = false; CHOSEN = null;
}


// ---------- the AI's decision, made visible: pipeline, who it picked and why, who it left alone, the result ----------
const face = id => id === "robot" ? "🤖" : (P[id] && P[id].img ? `<img src="${esc(P[id].img)}" alt="">` : esc(name(id)[0]));
const avatar = (id, cls = "av") => P[id].img ? `<img class="${cls}" src="${esc(P[id].img)}" alt="" style="background:${P[id].color}">`
  : `<span class="${cls} ini" style="background:${P[id].color}">${esc(P[id].name[0])}</span>`;
const STEPS = ["understand","outreach","clarify","relay","handover"];
function drawPipe(ph){
  if(ph) SEEN.add(ph);
  const cur = ph === "closed" ? STEPS.length : STEPS.indexOf(ph);
  document.querySelectorAll("#pipe li").forEach((li, i) => {
    li.className = cur < 0 && !ph ? "" : i < cur ? (SEEN.has(STEPS[i]) || i === 0 ? "done" : "skip") : i === cur ? "on" : "";
  });
  $("#pipe").classList.toggle("closed", ph === "closed");
}
const CHIP = {asked:["asked","a"], offer:["can help","o"], no:["can't","n"], chosen:["chosen ✓","c"], released:["thanked","r"]};
function drawBrain(){
  const picked = ORDER.filter(id => id !== asker && (ST[id] || WHY[id]));
  if(!picked.length) return;
  const sale = REQ && REQ.kind === "sale", hf = hourOf(clock);
  $("#brain").hidden = false;
  $("#picked").innerHTML = picked.map(id => {
    const c = sale && ST[id] === "offer" ? ["wants it","o"] : sale && ST[id] === "chosen" ? ["buyer ✓","c"] : CHIP[ST[id]] || ["picked","a"];
    return `<li>${avatar(id)}<span class="who-t"><b>${esc(P[id].name)}</b> <small>${esc(P[id].apt)}</small>
      <em>${WHY[id] ? "💡 " + esc(WHY[id]) : "picked from public facts"}</em></span><span class="st st-${c[1]}">${c[0]}</span></li>`;
  }).join("");
  const peace = ORDER.filter(id => id !== asker && !picked.includes(id)), zz = peace.filter(id => sleeping(id, hf));
  $("#peace").innerHTML = peace.map(id => `<span class="f${sleeping(id, hf) ? " zz" : ""}" title="${esc(P[id].name)} · ${sleeping(id, hf) ? "asleep, not disturbed" : "not asked"}">${avatar(id, "fa")}</span>`).join("");
  $("#peace-n").textContent = `${peace.length} left in peace${zz.length ? ` · ${zz.length} asleep` : ""}`;
  $("#reach").textContent = `${picked.length} of ${ORDER.length - 1} asked`;
}
function drawHelpers(){                                    // fairness: who has already helped in this building
  const el = $("#helpers"); if(!el) return;
  const ids = Object.keys(LEDGER).filter(id => P[id] && LEDGER[id] > 0).sort((a, b) => LEDGER[b] - LEDGER[a]);
  el.hidden = !ids.length;
  el.innerHTML = ids.length ? `<div class="peace-h"><span>🤝</span><b>Helpers so far</b><small>NearMind spreads requests out</small></div>
    <div class="helpers">${ids.map(id => `<span class="hp" title="${esc(P[id].name)} helped ${LEDGER[id]}×">${avatar(id, "fa")}<b>${LEDGER[id]}×</b></span>`).join("")}</div>` : "";
}
function drawResult({sale, item, from, to}){
  const asked = ORDER.filter(id => id !== asker && (ST[id] || WHY[id])).length, secs = T0 ? Math.round((Date.now() - T0) / 1000) : 0;
  const stat = (n, l) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`;
  $("#result").innerHTML = `<div class="res-h"><span class="big">✓</span><div><b>${sale ? "Sold" : "Delivered"}: ${esc(item)}</b>
    <small>${esc(name(from))} → ${esc(name(to))}'s door</small></div></div>
    <div class="stats">${stat(MSGS, "messages")}${stat(asked + "/" + (ORDER.length - 1), "asked")}${stat(ORDER.length - 1 - asked, "left in peace")}${stat(ROUNDS, "AI rounds")}${secs ? stat(secs + "s", demo ? "replay" : "start to finish") : ""}</div>
    ${DEMO_ID ? `<a class="readall" href="/chat/${DEMO_ID}" target="_blank" rel="noopener">Read the full conversation →</a>` : ""}`;
  $("#result").hidden = false; $("#brain").hidden = false;
  $("#brain-t").textContent = "How NearMind solved it";
}


// ---------- NearMind City: city map -> neighborhood -> building ----------
const fmt = n => n.toLocaleString("en-US");
const ROLE = {herself:"👩", himself:"👨", wife:"👩", husband:"👨", mother:"👵", father:"👴", grandmother:"👵", grandfather:"👴",
  son:"👦", daughter:"👧", brother:"🧑", sister:"👩", grandson:"👦", granddaughter:"👧", "daughter-in-law":"👩"};
const roleIcon = m => m.age <= 3 ? "👶" : ROLE[m.role] || "🧑";
const findHood = id => CITY.hoods.find(h => h.id === id);
const hoodOf = bid => CITY.hoods.find(h => h.buildings.some(b => b.id === bid));
function setView(v){
  VIEW = v; document.body.dataset.view = v;
  $("#cityview").hidden = v !== "city"; $("#hoodview").hidden = v !== "hood"; $("#bview").hidden = v !== "building";
  if(v !== "building") document.body.classList.remove("present");
  window.scrollTo({top:0});
}
function crumbs(parts){
  $("#crumbs").innerHTML = parts.map(([label, href], i) => i === parts.length - 1 ? `<span aria-current="page">${esc(label)}</span>` : `<a href="${href}">${esc(label)}</a>`).join('<span class="sep">›</span>');
}
function route(){
  if(!CITY) return;
  if(busy){ toast("Wait for this request to finish"); return; }
  const [, kind, id] = (location.hash || "#/").split("/");
  if(kind === "hood" && findHood(id)) return showHood(findHood(id));
  if(kind === "b" && hoodOf(id)) return showBuilding(id);
  showCity();
}
function countUp(el){
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;   // no counting animation for people who turned motion off
  el.querySelectorAll("[data-n]").forEach(x => { const n = +x.dataset.n, t0 = performance.now();
    if(still){ x.textContent = fmt(n); return; }
    const step = now => { const f = Math.min(1, (now - t0) / 900); x.textContent = fmt(Math.round(n * (1 - Math.pow(1 - f, 3)))); if(f < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step); });
}
const tower = (h, lit, robot, w = 34) => `<span class="tw" style="height:${h}px;width:${w}px">${robot ? '<i class="rb"></i>' : ""}${Array.from({length: 10}, (_, i) => `<b class="${(lit >> i) & 1 ? "on" : ""}"></b>`).join("")}</span>`;
const HPOS = {"al-noor":[22,30], "palm-bay":[20,72], "old-souq":[50,52], "crescent":[79,28], "falcon":[78,72]};
function showCity(){
  setView("city"); crumbs([["NearMind City", "#/"]]);
  $("#brand-sub").textContent = "City"; $("#brand-small").textContent = "one robot on every roof";
  $("#city-stats").innerHTML = [[CITY.hoods.length, "neighborhoods"], [CITY.buildings, "buildings"], [CITY.homes, "families"], [CITY.people, "people"]]
    .map(([n, l]) => `<div><b data-n="${n}">0</b><span>${l}</span></div>`).join("") + `<div class="robots"><b>🤖 ${CITY.buildings}</b><span>roof robots</span></div>`;
  countUp($("#city-stats"));
  const map = $("#citymap");
  map.innerHTML = `<svg class="ground" viewBox="0 0 1000 560" preserveAspectRatio="none" aria-hidden="true">
      <path class="sea" d="M0 430 Q120 400 210 470 T420 560 L0 560 Z"/>
      <path class="river" d="M500 0 C470 120 560 200 520 290 S430 420 470 560" />
      <g class="roads"><path d="M220 170 L500 290 L790 160"/><path d="M200 400 L500 290 L780 400"/><path d="M220 170 L200 400"/><path d="M790 160 L780 400"/></g>
      <g class="park">${[[120,90],[330,120],[640,90],[900,250],[380,470],[640,500],[930,500],[90,280]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="14"/><circle cx="${x + 18}" cy="${y + 8}" r="10"/>`).join("")}</g>
    </svg>
    <div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div>
    <div class="car k1">🚗</div><div class="car k2">🚌</div><div class="car k3">🚕</div>
    ${CITY.hoods.map((h, i) => { const [x, y] = HPOS[h.id] || [50, 50];
      return `<a class="hood" href="#/hood/${h.id}" style="left:${x}%;top:${y}%;--hc:${h.color};animation-delay:${i * 90}ms" aria-label="${esc(h.name)}, ${h.buildings.length} buildings, ${h.people} people">
        <span class="sky">${h.buildings.map((b, j) => tower(46 + ((j * 37 + i * 13) % 34), 0x3ff ^ (0x155 << (j % 2)), true, 26)).join("")}</span>
        <span class="lbl"><span class="hi">${h.icon}</span><b>${esc(h.name)}</b><small>${h.buildings.length} buildings · ${fmt(h.people)} people</small></span></a>`; }).join("")}`;
}
function showHood(h){
  setView("hood"); crumbs([["NearMind City", "#/"], [h.name, "#/hood/" + h.id]]);
  $("#brand-sub").textContent = h.name; $("#brand-small").textContent = h.desc;
  $("#hoodview").style.setProperty("--hc", h.color);
  $("#hood-hero").innerHTML = `<a class="back" href="#/">‹ City map</a><div class="hh"><span class="big">${h.icon}</span><div><h1>${esc(h.name)}</h1><p>${esc(h.desc)}</p></div></div>
    <div class="city-stats small"><div><b data-n="${h.buildings.length}">0</b><span>buildings</span></div><div><b data-n="${h.homes}">0</b><span>families</span></div><div><b data-n="${h.people}">0</b><span>people</span></div></div>`;
  countUp($("#hood-hero"));
  $("#hood-street").innerHTML = h.buildings.map((b, i) => `<a class="bcard${b.flagship ? " flag" : ""}" href="#/b/${b.id}" style="animation-delay:${i * 80}ms">
      <span class="bpic">${tower(150, 0x3ff ^ ((i * 0x2a5) & 0x3ff) | (b.flagship ? 0x3ff : 0), true, 92)}</span>
      <span class="binfo"><b>${esc(b.name)}</b>${b.flagship ? '<span class="star">★ Demo building · recorded runs</span>' : ""}
        <small>10 families · ${b.people} people</small>
        <span class="fams">${b.families.slice(0, 4).map(f => `<i>${esc(f)}</i>`).join("")}<i>+${b.families.length - 4} more</i></span>
        <span class="enter">Enter building →</span></span></a>`).join("");
}
async function showBuilding(bid){
  const h = hoodOf(bid), b = h.buildings.find(x => x.id === bid);
  setView("building"); crumbs([["NearMind City", "#/"], [h.name, "#/hood/" + h.id], [b.name, "#/b/" + bid]]);
  $("#brand-sub").textContent = b.name; $("#brand-small").textContent = `${h.name} · 10 families · ${b.people} people`;
  if(BID === bid) return;
  const d = await fetch(`/api/street/people?b=${encodeURIComponent(bid)}`).then(r => r.json());
  BID = bid; BMETA = d.building; P = d.people; ORDER = d.order; LEDGER = {}; drawHelpers();
  if(!ORDER.includes(asker)) asker = ORDER[0];
  document.querySelector(".demo-card").hidden = !BMETA.flagship;
  NMStreet.mount($("#scene"), P, id => pick(id), "/static/img/backdrop.jpg");
  fresh();
  setTimeout(() => { applyClock(); pick(asker, false); }, 50);
}
function drawFamily(){
  const p = P[asker]; if(!p || !p.members){ $("#family").hidden = true; return; }
  const ms = p.members;
  $("#family").hidden = false;
  $("#family").innerHTML = `<div class="fam-h">${avatar(asker)}<div><h2>The ${esc(p.family)} family</h2><small>Apartment ${esc(p.apt)} · ${ms.length} people · ${esc(p.icon)} ${esc((p.facts || [""])[0])}</small></div></div>
    <ul class="members">${ms.map((m, i) => `<li class="${i === 0 ? "contact" : ""}" style="animation-delay:${i * 40}ms"><span class="mi">${roleIcon(m)}</span><b>${esc(m.name)}</b><small>${esc(i === 0 ? "talks to NearMind" : m.role)} · ${m.age}</small></li>`).join("")}</ul>`;
}

// ---------- sending ----------
function setBusy(b){ busy = b; $("#go").disabled = b; $("#go").textContent = b ? "Working…" : "Send ➤"; }
function toast(t){ const el = $("#toast"); el.textContent = t; el.classList.add("show"); clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("show"), 2200); }

async function send(text){
  text = String(text || "").trim();
  if(!text) return;
  if(mode === "sell" && !/\b(sell|selling|for sale)\b/i.test(text)) text = "I'm selling " + text;
  if(busy){ toast("NearMind is still working on the last one"); return; }
  if(!$("#result").hidden) fresh();                          // the last request closed: a new message starts a new one
  setBusy(true); $("#quick").innerHTML = ""; $("#in").value = "";
  if(!T0) T0 = Date.now();
  try{
    const r = await fetch("/api/street/run", {method:"POST", headers:{"content-type":"application/json", "X-Sid":SID}, body:JSON.stringify({from:asker, text, clock, building:BID})});
    if(!r.ok){ const j = await r.json().catch(() => ({})); enqueue({t:"error", error:j.error || "Request failed"}); enqueue({t:"done"}); return; }
    const rd = r.body.getReader(), dec = new TextDecoder(); let buf = "";
    for(;;){
      const {done, value} = await rd.read(); if(done) break;
      buf += dec.decode(value, {stream:true});
      let i; while((i = buf.indexOf("\n")) >= 0){ const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1); if(line) enqueue(JSON.parse(line)); }
    }
  }catch(err){ enqueue({t:"error", error:"Can't reach the NearMind server. Is it running?"}); enqueue({t:"done"}); }
}

// ---------- who is asking ----------
function pick(id, focus = true){
  if(busy){ toast("Wait for this request to finish"); return; }
  if(id !== asker){ asker = id; fresh(); }
  renderWho(); NMStreet.asker(asker); drawFamily();
  $("#in").placeholder = `${name(asker)} needs… (e.g. ${asker === "sedra" ? "someone to watch a movie with" : "a ladder for 10 minutes"})`;
  if(focus) $("#in").focus({preventScroll:true});
}
function renderWho(){
  const hf = hourOf(clock);
  $("#who").innerHTML = ORDER.map(id => {
    const p = P[id], zz = sleeping(id, hf);
    return `<button type="button" role="radio" aria-checked="${id === asker}" data-id="${id}" class="${zz ? "zz" : ""}" title="${esc(p.name)} ${esc(p.family || "")} · Apt ${p.apt}${zz ? " · probably asleep" : ""}">${avatar(id)}<span class="nm">${esc(p.name)}</span><span class="ap">${esc(p.apt)}</span></button>`;
  }).join("");
}
function fresh(){
  NMStreet.clear(); Q.length = 0; $("#quick").innerHTML = ""; REQ = null; CHOSEN = null; CLOSED = false;
  $("#log").innerHTML = '<li class="empty">New request. Type it below and watch NearMind route it.</li>';
  $("#phase").textContent = "Waiting for a request";
  WHY = {}; ST = {}; MSGS = 0; ROUNDS = 0; SEEN = new Set(); DEMO_ID = null; T0 = 0;
  drawPipe(null); $("#brain").hidden = true; $("#result").hidden = true; $("#brain-t").textContent = "Why these neighbors?";
}

// ---------- recorded demos: real runs replayed instantly ----------
const DEMOS = [["movie","🎬 Movie night"],["ladder","🪜 Ladder at noon"],["charger","🔋 Charger at 00:30"],["sale","🏷️ Selling a bike"],["jump","🚗 Jump-start at 6 AM"],["arabic","🇸🇦 Ladder in Arabic"]];
async function playDemo(demoId){
  if(busy){ toast("Wait for this request to finish"); return; }
  if(!BMETA || !BMETA.flagship){ location.hash = "#/b/noor-tower"; await new Promise(r => setTimeout(r, 900)); }
  let d; try{ const r = await fetch(`/static/demos/${demoId}.json`); if(!r.ok) throw 0; d = await r.json(); }catch(e){ toast("That demo isn't recorded yet"); return; }
  demo = true; setBusy(true);
  asker = d.asker; fresh(); DEMO_ID = demoId; T0 = Date.now(); renderWho(); NMStreet.asker(asker); drawFamily();
  $("#in").placeholder = `${name(asker)} needs… (or tap another neighbor)`;
  clock = d.clock; document.querySelectorAll(".clock .chip").forEach(x => x.classList.toggle("on", x.dataset.clk === clock || (!x.dataset.clk && !clock)));
  if(![...document.querySelectorAll(".clock .chip")].some(x => x.classList.contains("on"))) document.querySelector('.clock [data-clk=""]').classList.remove("on");
  applyClock();
  logRow("think", "▶", "#e2f1ff", `Demo: <b>${esc(d.title)}</b> (a recorded real run at ${esc(d.clock)})`);
  d.events.forEach(e => enqueue(e));
}

// ---------- clock ----------
function hourOf(c){ if(!c){ const d = new Date(); return d.getHours() + d.getMinutes() / 60; } const [h, m] = c.split(":").map(Number); return h + m / 60; }
function sleeping(id, hf){ const [a, b] = P[id].sleep; return a > b ? (hf >= a || hf < b) : (hf >= a && hf < b); }
function periodOf(hf){ return hf >= 22 || hf < 6.5 ? "night" : hf < 9 ? "early morning" : hf < 17 ? "day" : "evening"; }
function applyClock(){
  const hf = hourOf(clock);
  NMStreet.period(periodOf(hf));
  NMStreet.asleep(Object.fromEntries(ORDER.map(id => [id, sleeping(id, hf)])));
  renderWho();
}

// ---------- theme ----------
let THM = null; try{ THM = localStorage.getItem("nm.theme"); }catch(e){}
function drawThm(){ if(THM) document.documentElement.dataset.theme = THM; const dark = document.documentElement.dataset.theme === "dark" || (!THM && matchMedia("(prefers-color-scheme: dark)").matches); $("#thm").textContent = dark ? "☀️" : "🌙"; }
$("#thm").onclick = () => { const dark = $("#thm").textContent === "☀️"; THM = dark ? "light" : "dark"; try{ localStorage.setItem("nm.theme", THM); }catch(e){} drawThm(); };

// ---------- wiring ----------
$("#f").onsubmit = e => { e.preventDefault(); send($("#in").value); };
$("#in").addEventListener("keydown", e => { if(e.key === "Enter" && !e.shiftKey){ e.preventDefault(); send($("#in").value); } });
$("#who").onclick = e => { const b = e.target.closest("[data-id]"); if(b) pick(b.dataset.id); };
$("#quick").onclick = e => { const b = e.target.closest("button"); if(b) send(b.textContent); };
$("#presets").onclick = e => { const m = e.target.closest("[data-more]"); if(m){ drawPresets(m.dataset.more === "1"); return; } const b = e.target.closest("[data-q]"); if(b) send(b.dataset.q); };
document.querySelector(".clock").onclick = e => {
  const b = e.target.closest("[data-clk]"); if(!b) return;
  document.querySelectorAll(".clock .chip").forEach(x => x.classList.toggle("on", x === b));
  clock = b.dataset.clk; applyClock();
};
$("#mode").onclick = e => {
  const b = e.target.closest("[data-mode]"); if(!b) return;
  mode = b.dataset.mode; document.querySelectorAll("#mode button").forEach(x => x.setAttribute("aria-pressed", x === b));
  $("#in").placeholder = mode === "sell" ? `What is ${name(asker)} selling, and for how much? e.g. my old bike, 150 SAR` : `${name(asker)} needs… (e.g. a ladder for 10 minutes)`;
  $("#in").focus({preventScroll:true});
};
$("#speed").onclick = () => { speed = speed === 1 ? 2 : 1; $("#speed").textContent = speed + "×"; $("#speed").setAttribute("aria-label", "Playback speed " + speed + "x"); };
$("#demos").innerHTML = DEMOS.map(([n, l], i) => `<button type="button" data-demo="${n}" title="Shortcut: ${i + 1}">${l}</button>`).join("");
$("#demos").onclick = e => { const b = e.target.closest("[data-demo]"); if(b) playDemo(b.dataset.demo); };
// ---------- WAICY: how it works, present mode, shortcuts ----------
const how = $("#how");
$("#howbtn").onclick = () => how.showModal();
how.addEventListener("click", e => { if(e.target === how) how.close(); });
function present(on){
  document.body.classList.toggle("present", on);
  if(on && document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => {});
  if(!on && document.fullscreenElement) document.exitFullscreen().catch(() => {});
}
$("#present").onclick = () => present(true);
$("#exitp").onclick = () => present(false);
document.addEventListener("fullscreenchange", () => { if(!document.fullscreenElement) document.body.classList.remove("present"); });
document.addEventListener("keydown", e => {
  if(e.target.closest("textarea,input") || e.ctrlKey || e.metaKey || e.altKey || how.open) return;
  const k = e.key.toLowerCase();
  if(VIEW !== "building"){ if(k === "?" || k === "i") how.showModal(); else if(k === "escape" && VIEW === "hood") location.hash = "#/"; return; }
  if(k >= "1" && k <= String(DEMOS.length)) playDemo(DEMOS[+k - 1][0]);
  else if(k === "p") present(!document.body.classList.contains("present"));
  else if(k === "escape") present(false);
  else if(k === "r") $("#reset").click();
  else if(k === "s") $("#speed").click();
  else if(k === "?" || k === "i") how.showModal();
});
try{ if(!localStorage.getItem("nm.seenHow")){ localStorage.setItem("nm.seenHow", "1"); setTimeout(() => how.showModal(), 700); } }catch(e){}

$("#reset").onclick = async () => {
  if(busy){ toast("Wait for this request to finish"); return; }
  try{ await fetch("/api/street/reset", {method:"POST", headers:{"X-Sid":SID, "content-type":"application/json"}, body:JSON.stringify({building:BID})}); }catch(e){}
  LEDGER = {}; drawHelpers(); fresh(); NMStreet.asker(asker); toast("Street cleared");
};

const FAV = ["Movie buddy","Sugar","Ladder","Drill","Charger","Umbrella","First aid","سلم"];
const ALL = PRESETS.flatMap(([, items]) => items), chip = ([ic, label, q]) => `<button type="button" data-q="${esc(q)}" title="${esc(q)}">${ic} ${label}</button>`;
function drawPresets(open){
  $("#presets").innerHTML = (open ? PRESETS.map(([g, items]) => `<span class="grp">${g}</span>` + items.map(chip).join("")).join("")
    : FAV.map(f => chip(ALL.find(x => x[1] === f))).join("")) + `<button type="button" class="more" data-more="${open ? 0 : 1}">${open ? "Less" : "More…"}</button>`;
}
drawPresets(false);

drawThm();
window.addEventListener("hashchange", route);
fetch("/api/city").then(r => r.json()).then(d => { CITY = d; route(); }).catch(() => toast("Can't reach the NearMind server"));
})();
