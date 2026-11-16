// NearMind Street page: controls, live timeline and pacing. The scene itself is window.NMStreet (Remotion).
(() => {
"use strict";
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let P = {}, ORDER = [], asker = "sedra", clock = "", busy = false, speed = 1, mode = "ask", demo = false;
let REQ = null, CHOSEN = null, CLOSED = false;            // what this request is, who was chosen, whether it closed
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
const STATE = {asked:"was asked",offer:"has it",no:"can't help",chosen:"was chosen ✓",released:"was thanked and released"};

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
      logRow("say", e.from === "robot" ? "🤖" : esc(name(e.from)[0]), color(e.from),
        `<b>${esc(name(e.from))}</b> → <b>${esc(name(e.to))}</b><span class="q">${esc(e.text)}</span>`);
      break;
    case "think":
      NMStreet.think(e.text);
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
      if(txt && e.state !== "asked") logRow("status", esc(name(e.who)[0]), color(e.who), `<b>${esc(name(e.who))}</b> ${txt}`);
    }
      break;
    case "typing":
      NMStreet.typing(e.who, e.on);
      break;
    case "phase":
      if(e.phase === "closed") CLOSED = true;
      $("#phase").textContent = PHASE[e.phase] || e.phase;
      break;
    case "quick":
      if(demo) break;
      $("#quick").innerHTML = e.options.map(o => `<button type="button">${esc(o)}</button>`).join("");
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
  CLOSED = false; CHOSEN = null;
}

// ---------- sending ----------
function setBusy(b){ busy = b; $("#go").disabled = b; $("#go").textContent = b ? "Working…" : "Send ➤"; }
function toast(t){ const el = $("#toast"); el.textContent = t; el.classList.add("show"); clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("show"), 2200); }

async function send(text){
  text = String(text || "").trim();
  if(!text) return;
  if(mode === "sell" && !/\b(sell|selling|for sale)\b/i.test(text)) text = "I'm selling " + text;
  if(busy){ toast("NearMind is still working on the last one"); return; }
  setBusy(true); $("#quick").innerHTML = ""; $("#in").value = "";
  try{
    const r = await fetch("/api/street/run", {method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify({from:asker, text, clock})});
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
  renderWho(); NMStreet.asker(asker);
  $("#in").placeholder = `${name(asker)} needs… (e.g. ${asker === "sedra" ? "someone to watch a movie with" : "a ladder for 10 minutes"})`;
  if(focus) $("#in").focus({preventScroll:true});
}
function renderWho(){
  const hf = hourOf(clock);
  $("#who").innerHTML = ORDER.map(id => {
    const p = P[id], zz = sleeping(id, hf);
    return `<button type="button" role="radio" aria-checked="${id === asker}" data-id="${id}" class="${zz ? "zz" : ""}" title="${esc(p.name)} · Apt ${p.apt}${zz ? " · probably asleep" : ""}"><img class="av" src="${p.img}" alt="" style="background:${p.color}"><span class="nm">${esc(p.name)}</span><span class="ap">${esc(p.apt)}</span></button>`;
  }).join("");
}
function fresh(){
  NMStreet.clear(); Q.length = 0; $("#quick").innerHTML = ""; REQ = null; CHOSEN = null; CLOSED = false;
  $("#log").innerHTML = '<li class="empty">New request. Type it below and watch NearMind route it.</li>';
  $("#phase").textContent = "Waiting for a request";
}

// ---------- recorded demos: real runs replayed instantly ----------
const DEMOS = [["movie","🎬 Movie night"],["ladder","🪜 Ladder at noon"],["charger","🔋 Charger at 00:30"],["sale","🏷️ Selling a bike"],["jump","🚗 Jump-start at 6 AM"]];
async function playDemo(demoId){
  if(busy){ toast("Wait for this request to finish"); return; }
  let d; try{ const r = await fetch(`/static/demos/${demoId}.json`); if(!r.ok) throw 0; d = await r.json(); }catch(e){ toast("That demo isn't recorded yet"); return; }
  demo = true; setBusy(true);
  asker = d.asker; fresh(); renderWho(); NMStreet.asker(asker);
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
  try{ await fetch("/api/street/reset", {method:"POST"}); }catch(e){}
  fresh(); NMStreet.asker(asker); toast("Street cleared");
};

const FAV = ["Movie buddy","Sugar","Eggs","Ladder","Drill","Charger","Umbrella","First aid"];
const ALL = PRESETS.flatMap(([, items]) => items), chip = ([ic, label, q]) => `<button type="button" data-q="${esc(q)}" title="${esc(q)}">${ic} ${label}</button>`;
function drawPresets(open){
  $("#presets").innerHTML = (open ? PRESETS.map(([g, items]) => `<span class="grp">${g}</span>` + items.map(chip).join("")).join("")
    : FAV.map(f => chip(ALL.find(x => x[1] === f))).join("")) + `<button type="button" class="more" data-more="${open ? 0 : 1}">${open ? "Less" : "More…"}</button>`;
}
drawPresets(false);

drawThm();
fetch("/api/street/people").then(r => r.json()).then(d => {
  P = d.people; ORDER = d.order;
  NMStreet.mount($("#scene"), P, id => pick(id), "/static/img/backdrop.jpg");
  setTimeout(() => { applyClock(); pick(asker, false); }, 50);
}).catch(() => toast("Can't reach the NearMind server"));
})();
