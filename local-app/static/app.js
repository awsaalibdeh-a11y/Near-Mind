"use strict";
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt=t=>esc(t).replace(/\*([^*\n]+)\*/g,"<b>$1</b>").replace(/(^|[\s(])_([^_\n]+)_(?=$|[\s).,!?])/g,"$1<i>$2</i>");
const NS="http://www.w3.org/2000/svg";
const PEOPLE=[
 {n:"Maya",role:"Neighbor 1 · #10",c:"#35d6a4",style:"casual & brief"},
 {n:"Ben",role:"Neighbor 2 · #12",c:"#66b8ff",style:"direct & functional"},
 {n:"Mrs. Cohen",role:"Neighbor 3 · #14",c:"#f2b560",style:"warm & formal"},
 {n:"Omar",role:"Neighbor 4 · #16",c:"#a99bff",style:"playful & quick"}];
const KNOWN={2:["Works from home","Night owl, groggy before 9","Short texts, porch drop-offs"],3:["Lives alone","Asleep ~21:30 to 07:00","Loves a thank-you note"],4:["Student, 19","Asleep ~03:00 to 11:00","Slang + emoji, helps any time after noon"]};
const STEPS=[["understand","Understand"],["outreach","Reach out"],["clarify","Clarify"],["relay","Relay"],["handover","Handover"],["closed","Closed"]];
const LAB={asked:"asked",offer:"has it",won:"chosen",done:"released",skip:"let sleep",idle:"idle"};
const KIND={route:"Route",translate:"Translate",done:"Done",insight:"Insight",safety:"Safety"};
const IC={
 send:'<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 20.5v-6.8l9-1.7-9-1.7V3.5L22 12 3 20.5z"/></svg>',
 sun:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
 moon:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>',
 check:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>'};

/* ---------------- scripted showcase ---------------- */
// ev: [phone, who, text, brain?]  brain: {parse:{item,qty,urg,subs,req?}, status, log:[kind,title,html], phase, ledger:[{item,frm,kind}], mem:{2:[..]}}
const SC={
salt:{label:"Salt",clock:"19:20",ev:[
[1,"me","anyone have salt?? halfway through dinner and out 😅"],
[1,"ai","Got it Maya! Salt, about 1 tsp, urgent. Table, sea or kosher all work. Asking Ben and Mrs. Cohen now, sit tight.",
 {phase:"understand",parse:{item:"Salt",qty:"≈ 1 tsp",urg:"High · dinner in progress",subs:["table salt","sea salt","kosher salt"]},status:{2:"asked",3:"asked"},log:["route","Parsed request","Item <u>salt</u>, qty ~1 tsp, urgent. Both neighbors are awake at 19:20, so ping Ben and Mrs. Cohen."]}],
[2,"ai","Maya (#10) needs a little salt for dinner. Any kind. Can you spare some? No problem if not."],
[3,"ai","Good evening Mrs. Cohen. Maya at #10 is short of salt for tonight's dinner and would be grateful for a spoonful of any kind. Only if it's no trouble at all, and thank you either way.",
 {phase:"outreach",log:["route","Style matching","Same request, two voices: Ben gets <u>direct</u>, Mrs. Cohen gets <u>warm &amp; formal</u>. No pressure to either."]}],
[2,"me","got the pink stuff"],
[3,"me","Only the coarse baking kind, dear. Give me 5 minutes and I'll find a jar."],
[2,"ai","Check: 'pink stuff' = Himalayan pink salt? Fine for cooking, same taste. OK to hand over?",
 {phase:"clarify",log:["translate","Ambiguity: Ben","<s>\"got the pink stuff\"</s><br>→ probably <u>Himalayan pink salt</u>. Edible, same taste. Confirming before telling Maya."]}],
[2,"me","yep himalayan. grinder, ok to grab",{status:{2:"offer"},mem:{2:["Keeps pink salt in a grinder"]}}],
[3,"ai","Is 'coarse baking kind' coarse kosher salt? That works well too. A small cup is plenty.",
 {status:{3:"offer"},log:["translate","Ambiguity: Mrs. Cohen","<s>\"only the coarse baking kind\"</s><br>→ <u>coarse kosher salt</u>, ready in ~5 min. Use ~1.5x since it's chunkier."]}],
[1,"ai","Two offers, Maya 🎉\n• *Ben*: Himalayan pink salt in a grinder, ready now (same taste, just grind it)\n• *Mrs. Cohen*: coarse kosher salt, ready in ~5 min (use ~1.5x, it's chunkier)\nBen is faster. Lock it in with him?",
 {phase:"relay",log:["route","Relayed to Maya","Translated both replies into plain terms, in Maya's casual style, ranked by speed."]}],
[1,"me","ben pls!!",{status:{2:"won"}}],
[2,"ai","Maya says yes please 🙏 Porch drop at #10 okay? She'll leave the light on. Ring once, no need to chat.",
 {phase:"handover",log:["done","Logistics","Porch drop at #10, light on, one ring, no chat. Matches what I know about Ben: <u>porch drop-offs</u>."]}],
[2,"me","on my way 👍"],
[3,"ai","Ben already had some on hand, Mrs. Cohen, so no need to trouble yourself tonight. Maya sends her warmest thanks and would love to bring you a slice of dessert tomorrow.",
 {status:{3:"done"},log:["done","Released politely","Mrs. Cohen thanked, nothing owed, offered a small gesture back."]}],
[3,"me","How thoughtful of her, dear. Any time.",{mem:{3:["Keeps coarse kosher salt for pickling"]}}],
[1,"ai","Done ✅ Ben is dropping the grinder on your porch in ~2 min. Say thanks when you see him?",
 {phase:"closed",ledger:[{item:"Pink salt",frm:2,kind:"gift"}],log:["insight","Favor recorded","Salt is a consumable, so it goes in the ledger as a <u>thank-you owed</u>, not a return."]}]]},
ladder:{label:"2 AM ladder",clock:"02:10",ev:[
[1,"me","does anyone have a ladder? smoke detector is chirping at 2am lol"],
[1,"ai","Oof, the chirp 😅 One ladder for ~15 min. Checking with Ben first, he's up late.",
 {phase:"understand",parse:{item:"Ladder",qty:"1 · ~15 min",urg:"Medium · tonight",subs:["step stool","folding step ladder"]},status:{3:"skip"},log:["insight","Quiet hours","It's 02:10. <u>Mrs. Cohen is asleep</u> (quiet hours 21:30 to 07:00), so I won't wake her unless Ben can't help."]}],
[2,"ai","Maya (#10) needs a ladder ~15 min tonight for a smoke detector. Got one to lend?",{status:{2:"asked"},phase:"outreach"}],
[2,"me","got a 6ft one. the long thing in the garage"],
[2,"ai","'The long thing': is it a 6 ft folding step ladder or an extension ladder?",
 {phase:"clarify",log:["translate","Ambiguity: Ben","<s>\"the long thing in the garage\"</s><br>→ unclear type. Asking: <u>step ladder</u> or <u>extension</u>? A step ladder is what Maya needs."]}],
[2,"me","step. folds. aluminium",{status:{2:"offer"},mem:{2:["Owns a 6ft aluminium step ladder"]}}],
[1,"ai","Ben has a 6 ft aluminium folding step ladder, ready now 🪜 Perfect for a smoke detector. Want me to ask him? Mrs. Cohen is asleep, so I left her out.",
 {phase:"relay",log:["safety","Safety check","Aluminium folding step ladder is stable for a ceiling detector. Reminder: open it fully and lock the braces."]}],
[1,"me","ben pls, thank you!!",{status:{2:"won"}}],
[2,"ai","Maya says yes, thanks 🙏 Can you leave it by her front door? She'll return it tomorrow evening.",
 {phase:"handover",log:["done","Logistics","Leave at front door, return tomorrow evening. Nobody has to meet at 2 am."]}],
[2,"me","left by the door"],
[1,"ai","Ladder is at your front door ✅ Return it tomorrow evening and I'll nudge you. Good luck with the chirp!",
 {phase:"closed",ledger:[{item:"6ft step ladder",frm:2,kind:"lend"}],log:["done","Loop closed","Handed over without waking anyone. Logged as a <u>loan to return</u>."]}]]},
eggs:{label:"Eggs",clock:"08:05",ev:[
[1,"me","can i borrow 2 eggs? making pancakes for the kids"],
[1,"ai","Pancakes, love it 🥞 2 eggs, flexible on kind. Asking Ben and Mrs. Cohen.",
 {phase:"understand",parse:{item:"Eggs",qty:"2",urg:"Low · this morning",subs:["any size","farm eggs","flax egg (if none)"]},status:{2:"asked",3:"asked"},log:["route","Parsed request","Item <u>eggs</u>, qty 2, low urgency. Ben is usually groggy before 9, so Mrs. Cohen may answer first."]}],
[2,"ai","Maya (#10) needs 2 eggs for pancakes. Spare any?"],
[3,"ai","Good morning Mrs. Cohen. Maya at #10 is making pancakes for the children and is short two eggs. Would you be able to spare them? Only if convenient.",{phase:"outreach"}],
[2,"me","give me 5"],
[3,"me","Only the brown ones from my sister's hens, dear. Very fresh."],
[2,"ai","'Give me 5': five minutes, or 5 eggs?",
 {phase:"clarify",log:["translate","Ambiguity: Ben","<s>\"give me 5\"</s><br>→ could mean <u>5 minutes</u> or <u>5 eggs</u>. Asking before telling Maya anything."]}],
[2,"me","5 min. need to find the carton",{status:{2:"offer"}}],
[3,"ai","Brown farm eggs are perfect, thank you. Shall Maya pop round?",
 {status:{3:"offer"},log:["translate","Ambiguity: Mrs. Cohen","<s>\"only the brown ones\"</s><br>→ <u>fresh brown farm eggs</u>, available now. Totally fine for pancakes."]}],
[1,"ai","Two offers 🥚\n• *Ben*: ready in ~5 min (carton hunt)\n• *Mrs. Cohen*: fresh brown farm eggs, ready now\nMrs. Cohen is faster. OK?",
 {phase:"relay",log:["route","Relayed to Maya","Ranked by speed. Mrs. Cohen is ready now, Ben needs ~5 min."]}],
[1,"me","mrs cohen! the kids are hungry",{status:{3:"won"}}],
[3,"ai","Maya would love to collect them now, Mrs. Cohen. She'll be at your door in two minutes and will bring a pancake over as a thank-you.",
 {phase:"handover",log:["done","Logistics","Doorstep hand-off at #14, Maya collects. Pancake as a thank-you."]}],
[3,"me","Lovely. I'll have them ready, dear.",{mem:{3:["Keeps hens' eggs from her sister"]}}],
[2,"ai","Mrs. Cohen already has eggs, Ben, so you're off the hook. Thank you for checking!",{status:{2:"done"}}],
[1,"ai","Eggs are ready at Mrs. Cohen's door (#14) ✅ Go now. Pancakes await!",
 {phase:"closed",ledger:[{item:"2 brown eggs",frm:3,kind:"gift"}],log:["insight","Favor recorded","Mrs. Cohen loves a thank-you. A pancake is already planned, so I'll log it as owed."]}]]},
charger:{label:"Night charger",clock:"23:40",ev:[
[1,"me","phone's at 2% and my charger just died 😭 anyone got a spare?"],
[1,"ai","On it! One phone charger, tonight. It's 23:40, so I'll let Mrs. Cohen sleep and try Ben and Omar, the night owls.",
 {phase:"understand",parse:{item:"Phone charger",qty:"1 · overnight",urg:"High · phone at 2%",subs:["USB-C brick + cable","power bank"]},status:{2:"asked",4:"asked",3:"skip"},log:["insight","Quiet hours","It's 23:40: <u>Mrs. Cohen is asleep</u>. Ben and Omar are both night owls, so I ping those two only."]}],
[2,"ai","Maya (#10) needs a phone charger tonight. Got a spare?"],
[4,"ai","yo Omar 👋 Maya at #10 needs a phone charger rn, hers died. got one she can borrow?",
 {phase:"outreach",log:["route","Style matching","Same ask, two voices: Ben gets <u>direct</u>, Omar gets <u>playful &amp; quick</u>."]}],
[2,"me","somewhere in a drawer. give me 10"],
[4,"me","bet. got the beast one ⚡ come thru whenever"],
[4,"ai","'The beast': that's your 65W USB-C fast charger, right? Cable included?",
 {phase:"clarify",log:["translate","Ambiguity: Omar","<s>\"the beast one ⚡\"</s><br>→ probably his <u>65W USB-C fast charger</u>. Confirming the cable before telling Maya."]}],
[4,"me","yup 65w + cable. door's open ngl",{status:{4:"offer"},mem:{4:["Owns a 65W USB-C fast charger"]}}],
[1,"ai","Two options 🔌\n• *Omar*: 65W fast charger + cable, ready right now\n• *Ben*: has one somewhere, ~10 min of drawer digging\nOmar is faster and his charges quick. Go with him?",
 {phase:"relay",status:{2:"offer"},log:["route","Relayed to Maya","Ranked by speed at 23:40: Omar is ready now, Ben needs ~10 minutes of searching."]}],
[1,"me","omar pls 🙏",{status:{4:"won"}}],
[4,"ai","Maya says yes please 🙏 She'll pop over to #16 in 2 min, doorstep handoff ok?",
 {phase:"handover",log:["done","Logistics","Quick doorstep hand-off at #16. Nobody else gets woken up."]}],
[4,"me","say less. it's by the door 🛹"],
[2,"ai","Sorted already Ben, thanks for digging. Stand down.",
 {status:{2:"done"},log:["done","Released politely","Ben thanked and released in his own style: short, no fuss."]}],
[2,"me","👍"],
[1,"ai","Charger's waiting by Omar's door (#16) ✅ It's his good 65W one, so bring it back tomorrow and I'll remind you.",
 {phase:"closed",ledger:[{item:"65W fast charger",frm:4,kind:"lend"}],log:["insight","Favor recorded","A charger goes back, so it's logged as a <u>loan to return</u>, not a gift."]}]]},
ask:{label:"Ben asks Maya",clock:"17:40",ev:[
[2,"me","hey does maya have a bike pump? tyre's flat"],
[2,"ai","On it Ben, I'll check with Maya.",
 {phase:"understand",parse:{item:"Bike pump",qty:"1 · ~10 min",urg:"Low · this evening",subs:[],req:"Ben"},status:{2:"asked"},log:["route","Neighbor is asking","<u>Ben</u> needs something. Maya is the helper, so I ask her first and only relay her answer."]}],
[1,"ai","Hey Maya 👋 Ben (#12) has a flat tyre and asked if you have a bike pump he could borrow for ~10 min. Can you help?",{phase:"relay"}],
[1,"me","yes! it's by the front door, he can grab it",{status:{2:"won"}}],
[2,"ai","Maya says yes: the pump is by her front door at #10. Grab it anytime and drop it back when you're done 👍",
 {phase:"handover",log:["done","Logistics","Pump waits on Maya's porch. No need to meet, matching Ben's style."]}],
[2,"me","nice. grabbing now"],
[1,"ai","Done ✅ Ben is collecting the pump from your porch. I'll make sure it comes back tonight.",
 {phase:"closed",log:["insight","Goodwill","You helped Ben today. Next time you need something, he's a good first ask."]}]]}};

/* ---------------- state ---------------- */
let mode="show",cur="salt",i=0,paused=false,speed=1,run=0,PUB=false;
let busy=false,pn=0,seen=0,pendingQ=null,streaming=false,mpane=1,TAB="log";
let PARSE=null,PHASE=null,STAT={2:"",3:"",4:""},LOGS=[],unread={};
let ST={clock:{label:"",sim:false},learned:{2:[],3:[],4:[]},ledger:[],history:[],asks:{2:0,3:0,4:0}};
const wait=ms=>new Promise(r=>setTimeout(r,ms/speed));
const realLabel=()=>new Date().toTimeString().slice(0,5);
const curLabel=()=>ST.clock.sim&&ST.clock.label?ST.clock.label:realLabel();
const hfOf=l=>{const[a,b]=l.split(":");return +a+b/60};
const periodOf=l=>{const h=hfOf(l);return h>=22||h<6.5?"night":h<9?"early morning":h<17?"day":"evening"};
function stamp(){if(ST.clock.sim&&ST.clock.label){const m=Math.round(hfOf(ST.clock.label)*60)+Math.floor(pn/2);return String(Math.floor(m/60)%24).padStart(2,"0")+":"+String(m%60).padStart(2,"0")}return realLabel()}
function presence(k){const h=hfOf(curLabel());
 if(k===1)return{t:"Neighbor 1 · #10",c:"on"};
 if(k===3&&(h>=21.5||h<7))return{t:"asleep · quiet hours",c:"sleep"};
 if(k===4&&h>=3&&h<11)return{t:"asleep · quiet hours",c:"sleep"};
 if(k===2&&h>=3&&h<8.5)return{t:"groggy · just waking",c:"idle"};
 return{t:"online · "+PEOPLE[k-1].role.split("· ")[1],c:"on"}}

/* ---------------- build ---------------- */
const SUG=[["🧂 Salt","anyone have salt?? halfway through dinner and out 😅"],["🪜 Ladder","does anyone have a ladder? smoke detector is chirping at 2am lol"],["🥚 Eggs","can i borrow 2 eggs? making pancakes for the kids"],["🔌 Charger","does anyone have a phone charger i can borrow? mine is dead"],["🪛 Drill","need to borrow a drill for 20 min to hang a shelf"],["🥛 Oat milk","anyone have oat milk? my coffee is sad"],["🎮 Controller","anyone got a spare controller i can borrow? mine's drifting"]];
const ASKS={2:["hey does maya have a bike pump? tyre's flat","got any milk maya? out for my coffee","can maya spare a phone charger? mine died"],3:["Good evening, dear. Might Maya have a lemon she could spare?","Dear, does Maya happen to own a torch? The lights keep flickering.","Would Maya be able to help carry my shopping up the steps, dear?"],4:["yo does maya have an hdmi cable? movie night emergency 😭","any chance maya's got scissors? package situation rn","can maya lend a whisk? attempting pancakes and it's going badly"]};
const MAP=`<svg id="map" viewBox="0 0 420 160" role="img" aria-label="Street map">
<circle class="star" cx="30" cy="16" r="1.2"/><circle class="star" cx="120" cy="30" r="1"/><circle class="star" cx="300" cy="14" r="1.2"/><circle class="star" cx="356" cy="40" r="1"/><circle class="star" cx="70" cy="44" r="1"/>
<circle class="sun" cx="390" cy="24" r="9"/><circle class="moonc" cx="394" cy="21" r="8"/>
<g class="road"><rect x="0" y="122" width="420" height="22"/><path d="M0 133H420"/></g>
<path id="l1" class="lnk" d="M210 46Q130 60 55 72"/><path id="l2" class="lnk" d="M210 46Q185 60 160 72"/><path id="l3" class="lnk" d="M210 46Q238 60 265 72"/><path id="l4" class="lnk" d="M210 46Q295 60 370 72"/>
${[1,2,3,4].map(k=>{const x=[55,160,265,370][k-1];return `<g class="house" id="h${k}"><polygon class="roof" points="${x-30},94 ${x},72 ${x+30},94"/><rect class="body" x="${x-24}" y="94" width="48" height="28" rx="3"/><rect class="win" x="${x-17}" y="100" width="9" height="9" rx="1"/><rect class="win" x="${x+8}" y="100" width="9" height="9" rx="1"/><rect x="${x-4}" y="106" width="8" height="16" rx="1" fill="#10151a"/><text x="${x}" y="156">${["#10 Maya","#12 Ben","#14 Mrs. Cohen","#16 Omar"][k-1]}</text></g>`}).join("")}
<g id="hub"><circle class="hubring" cx="210" cy="32" r="16"/><circle class="hubc" cx="210" cy="32" r="14"/><text class="hubt" x="210" y="37">N</text></g></svg>`;
const popHTML=(k,pre="")=>`<div class="pop" id="pop${pre}${k}"><h5>${PEOPLE[k-1].n} asks Maya for…</h5>${ASKS[k].map(t=>`<button class="q" data-sendas="${k}">${esc(t)}</button>`).join("")}<form data-askform="${k}"><input placeholder="Or type what ${PEOPLE[k-1].n} says…" maxlength="200"><button class="btn pri">Send</button></form></div>`;
const INP=`<div class="inp" id="inp"><div class="sug" id="sug">${SUG.map(s=>`<button data-q="${esc(s[1])}">${s[0]}</button>`).join("")}</div><form id="f"><textarea id="in" rows="1" placeholder="Tell NearMind what you need, then press Done…" maxlength="600"></textarea><button class="send done" title="Done: send it to NearMind">Done ✓</button></form></div>`;
/* ---------- apartment view: how NearMind reaches the houses ---------- */
const UNITS={1:"#10",2:"#12",3:"#14",4:"#16"};
function streetIntro(){const list=n=>n.length>1?n.slice(0,-1).join(", ")+" and "+n[n.length-1]:n[0]||"";
 const real=[2,3,4].filter(k=>NB[k]).map(k=>"<b>"+esc(PEOPLE[k-1].n)+"</b>"),ai=[2,3,4].filter(k=>!NB[k]).map(k=>"<b>"+esc(PEOPLE[k-1].n)+"</b>");
 let t="";if(real.length)t+=list(real)+(real.length>1?" are real neighbors":" is a real neighbor")+" on WhatsApp: NearMind messages them for you and waits for their real answer. ";
 if(ai.length)t+=(real.length?"":"Your neighbors ")+list(ai)+(ai.length>1?" are AI and answer":" is AI and answers")+" in their own vague way. Tap ⚡ to see "+(ai.length>1?"them":"them")+" ask <i>you</i> for something.";
 return t}
function unitHTML(k){const p=PEOPLE[k-1];return `<div class="unit" id="u${k}" style="--pc:${p.c}"><div class="ut"><div class="uav" style="background:${p.c}">${p.n[0]}</div><div><b>${p.n}${k===1?" (you)":""}</b><small>Apartment ${UNITS[k]}</small></div>${k>1?`<span class="ust" id="ust${k}">idle</span>`:""}</div>${k>1?`<button class="rb" id="rb${k}" hidden></button>`:""}<div class="ubub" id="ub${k}"></div><div class="utyp" id="ut${k}"><b></b><b></b><b></b></div><div class="zz">Z z z</div>${k>1&&!(mode==="play"&&NB[k])?`<button class="uask" data-ask="a${k}" title="Simulate ${p.n} asking Maya for something">⚡</button>${popHTML(k,"a")}`:""}</div>`}
const aptHTML=()=>`<section class="pane" id="apt" data-p="day"><div class="apt-h"><div><b>Maple Court</b><small>Watch NearMind reach your neighbors</small></div><span class="apt-ph" id="aphase">Waiting for your request</span></div><div class="bld-wrap"><div class="rmwrap"><div id="rm"></div><div class="arow"><span>⚡ Simulate a neighbor asking Maya:</span>${[2,3,4].filter(k=>!(mode==="play"&&NB[k])).map(k=>`<span class="ak"><button class="btn" data-ask="a${k}">${PEOPLE[k-1].n}</button>${popHTML(k,"a")}</span>`).join("")}</div></div></div></section>`;
function aptPts(){const f=$("#facade");if(!f)return null;const fr=f.getBoundingClientRect(),c=el=>{const r=el.getBoundingClientRect();return[r.left-fr.left+r.width/2,r.top-fr.top+r.height/2]};return{fr,hub:c($("#hubn")),u:[1,2,3,4].map(k=>c($("#u"+k)))}}
function drawWires(){const w=$("#wires"),P=aptPts();if(!w||!P||!P.fr.width)return;[w,$("#pkts")].forEach(x=>x.setAttribute("viewBox",`0 0 ${P.fr.width} ${P.fr.height}`));
 w.innerHTML=P.u.map((u,k)=>`<line id="w${k+1}" x1="${P.hub[0]}" y1="${P.hub[1]}" x2="${u[0]}" y2="${u[1]}"/>`).join("")}
function aptPing(ph,who){window.NMApt&&NMApt.ping(ph,who);const w=$("#pkts"),P=aptPts();if(!w||!P||!P.fr.width)return;const c=document.createElementNS(NS,"circle");c.setAttribute("r",7);c.setAttribute("fill",who==="ai"?"#17c394":PEOPLE[ph-1].c);c.setAttribute("stroke","#fff");c.setAttribute("stroke-width",2);
 const u=P.u[ph-1];who==="ai"?fly(P.hub,u,0,c,800,w):fly(u,P.hub,0,c,800,w);const l=$("#w"+ph);l&&(l.classList.add("hot"),setTimeout(()=>l.classList.remove("hot"),1000))}
function aptSay(ph,who,text){window.NMApt&&NMApt.say(ph,who,text);const b=$("#ub"+ph);if(!b)return;const t=text.length>150?text.slice(0,147)+"…":text;b.innerHTML=`<span class="bw">${who==="ai"?"NearMind":esc(PEOPLE[ph-1].n)}</span>${fmt(t)}`;b.className="ubub show "+who;b.style.animation="none";void b.offsetWidth;b.style.animation=""}
const aptTyp=(ph,on)=>{window.NMApt&&NMApt.typing(ph,on);const t=$("#ut"+ph);t&&t.classList.toggle("on",on)};
let STAGE="talk";
function setStage(s){STAGE=s;setTimeout(()=>{renderReal();realPoll()},60);document.body.dataset.stage=mode==="play"?s:"show";
 const vw=$("#vw");if(vw){vw.style.display=mode==="play"&&s!=="talk"?"":"none";const nr=innerWidth<=600;vw.textContent=s==="detail"?(nr?"🏢":"🏢 Apartment view"):(nr?"📊":"📊 Full dashboard");vw.title=s==="detail"?"Apartment view":"Full dashboard"}
 if(mode==="play"&&innerWidth<=860){const T=s==="detail"?[["Maya",1],["Ben",2],["Cohen",3],["Omar",4],["Brain",5]]:[["Chat",1],["Building",6]];
  $("#mtabs").innerHTML=T.map(([n,k])=>`<button data-p="${k}">${n}</button>`).join("");setPane(s==="build"?6:s==="talk"?1:1)}
 requestAnimationFrame(()=>requestAnimationFrame(drawWires))}
addEventListener("resize",()=>drawWires());
function build(){
 const live=mode==="play";
 const phone=k=>{const p=PEOPLE[k-1];
  return `<section class="pane phone${mpane===k?" show":""}" id="ph${k}" style="--pc:${p.c}"><div class="hd"><div class="av" style="background:${p.c}" id="av${k}">${p.n[0]}</div><div><b>${p.n}${live&&k===1?" (you)":""}</b><small id="pr${k}"></small></div><span class="sty">${p.style}</span>${live&&k>1?`<button class="btn ask" data-ask="${k}" title="Simulate ${p.n} asking Maya for something">⚡ Ask</button>${popHTML(k)}`:""}</div><div class="chat" id="c${k}"><div class="tag">Private chat with NearMind</div>${live&&k===1?`<div class="hint"><div class="hh">Hi Maya 👋</div>Ask NearMind for a favor in your own words. ${streetIntro()}<div class="starters">${SUG.slice(0,4).map(s=>`<button class="starter" data-q="${esc(s[1])}"><b>${s[0]}</b><span>${esc(s[1].slice(0,38))}…</span></button>`).join("")}</div></div>`:""}</div>${live&&k===1?INP:""}</section>`};
 $("#grid").innerHTML=phone(1)+phone(2)+phone(3)+phone(4)+
 `<section class="pane${mpane===5?" show":""}" id="mind"><div class="mh"><span class="dot"></span><b>NearMind brain</b><span class="live" id="live"></span><span class="clk" id="clk"></span><button class="ib" id="dg" title="Street digest: NearMind summarises the day">✨</button><button class="ib" id="ex" title="Export the whole conversation">⬇</button></div>
 <div class="street" id="street">${MAP}</div>
 <div class="rqwrap" id="req"></div><div class="nst" id="nst"></div><div class="stats" id="stats"></div>
 <div class="tabs2" id="tabs2"><button class="t2" data-t="log">Decisions</button><button class="t2" data-t="ledger">Favors <em id="nled">0</em></button><button class="t2" data-t="nb">Neighbors</button><button class="t2" data-t="hist">History</button></div>
 <div class="tb" id="tb"></div></section>`+aptHTML();
 $("#mtabs").innerHTML=[["Maya",1],["Ben",2],["Cohen",3],["Omar",4],["Brain",5]].map(([n,k])=>`<button data-p="${k}" class="${mpane===k?"on":""}">${n}</button>`).join("");
 renderAll();mountApt();
}
function mountApt(){if(window.NMApt&&$("#rm")){NMApt.clear();NMApt.mount($("#rm"),PEOPLE.map((p,i)=>({n:p.n,c:p.c,apt:UNITS[i+1]})));NMApt.busy(busy);renderClock();mapState()}}
function setPane(k){mpane=k;unread[k]=false;$$(".grid>.pane").forEach((e,n)=>e.classList.toggle("show",n+1===k));$$("#mtabs button").forEach(b=>{const p=+b.dataset.p;b.classList.toggle("on",p===k);b.classList.toggle("un",!!unread[p])})}
$("#mtabs").onclick=e=>{const p=e.target.dataset.p;p&&setPane(+p)};

/* ---------------- render ---------------- */
function renderAll(){renderPipe();renderReq();renderNst();renderTab();renderClock();renderPres();mapState();renderStats()}
/* ---- request timer, stats, karma ---- */
let T0=0,DUR=[],CLOSED_AT=0;
const fmtDur=s=>s<60?Math.round(s)+"s":Math.floor(s/60)+"m "+String(Math.round(s%60)).padStart(2,"0")+"s";
function karma(k){const n=PEOPLE[k-1].n;let gave=0,got=0;ST.history.forEach(x=>{if(x.req&&x.req!=="Maya"){if(x.req===n)got++}else if(x.who===n)gave++});return{gave,got}}
function renderStats(){const el=$("#stats");if(!el)return;
 const open=ST.ledger.filter(l=>l.open).length,avg=DUR.length?fmtDur(DUR.reduce((a,b)=>a+b,0)/DUR.length):"–";
 const tot=ST.history.length;
 const st=[[tot,"closed"],[open,"open favors"],[avg,"avg close"],[Object.values(ST.asks||{}).reduce((a,b)=>a+b,0),"pings sent"]];
 el.innerHTML=st.map(([v,l])=>`<div class="sx"><b>${v}</b><span>${l}</span></div>`).join("")}
setInterval(()=>{const e=$("#rqt");if(e&&T0&&!CLOSED_AT)e.textContent="⏱ "+fmtDur((Date.now()-T0)/1000)},1000);
function confetti(){const c=document.createElement("canvas");c.className="confetti";c.width=innerWidth;c.height=innerHeight;document.body.append(c);
 const x=c.getContext("2d"),cols=["#17c394","#2f8fe6","#e08a2e","#7c5ce6","#e5533d","#f2c14e"],P=[...Array(90)].map(()=>({x:innerWidth*(.3+Math.random()*.4),y:innerHeight*.35,vx:(Math.random()-.5)*11,vy:-Math.random()*11-3,r:3+Math.random()*4,c:cols[Math.random()*6|0],a:Math.random()*6}));
 const t0=performance.now();(function f(t){const k=(t-t0)/1700;x.clearRect(0,0,c.width,c.height);P.forEach(p=>{p.vy+=.35;p.x+=p.vx;p.y+=p.vy;p.a+=.2;x.globalAlpha=Math.max(0,1-k);x.fillStyle=p.c;x.save();x.translate(p.x,p.y);x.rotate(p.a);x.fillRect(-p.r,-p.r/2,p.r*2,p.r);x.restore()});k<1?requestAnimationFrame(f):c.remove()})(t0)}
let REPLAY=false;
function onClosed(){if(CLOSED_AT)return;CLOSED_AT=Date.now();const d=T0?(CLOSED_AT-T0)/1000:0;if(d>3&&!REPLAY){DUR.push(d);const e=$("#rqt");e&&(e.textContent="✓ closed in "+fmtDur(d))}if(!REPLAY){confetti();toast("Loop closed"+(d>3?" in "+fmtDur(d):"")+" 🎉")}renderStats()}
function modal(title,html){$$(".mdl").forEach(x=>x.remove());const m=document.createElement("div");m.className="mdl";m.innerHTML=`<div class="mbox"><div class="mt"><b>${title}</b><button class="ib" data-x>✕</button></div><div class="mb">${html}</div></div>`;m.onclick=e=>{if(e.target===m||e.target.closest("[data-x]"))m.remove()};document.body.append(m)}
async function digest(){if(mode!=="play"){toast("Switch to Live to get a digest of your street");return}
 modal("Street digest ✨",'<div class="typing"><span>NearMind is writing</span> <b></b><b></b><b></b></div>');
 try{const j=await (await F("/api/digest",{method:"POST",headers:{"content-type":"application/json"},body:"{}"})).json();const b=$(".mdl .mb");b&&(b.innerHTML=`<div class="dtext">${esc(j.text).replace(/\n/g,"<br>")}</div>`)}catch(e){const b=$(".mdl .mb");b&&(b.textContent="Couldn't reach the server.")}}
function exportChat(){let t="NearMind conversation · "+new Date().toLocaleString()+"\n";
 [1,2,3,4].forEach(k=>{t+="\n=== "+PEOPLE[k-1].n+" ===\n";$$("#c"+k+" .m").forEach(m=>{const w=m.classList.contains("ai")?"NearMind":PEOPLE[k-1].n;t+=w+": "+($(".bd",m)||m).innerText.trim()+"\n"})});
 t+="\n=== Decisions ===\n"+LOGS.map(l=>"["+l.time+"] "+l.kind.toUpperCase()+" · "+l.title+": "+l.html.replace(/<[^>]+>/g,"")).join("\n");
 const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([t],{type:"text/plain"}));a.download="nearmind-conversation.txt";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);toast("Conversation exported")}
function derive(){if(!PARSE)return -1;const v=Object.values(STAT);if(v.includes("won"))return 4;if(v.includes("offer"))return 3;if(v.includes("asked"))return 1;return 0}
function renderPipe(){let n=PHASE?STEPS.findIndex(s=>s[0]===PHASE):derive();
 const h=curLabel(),per=periodOf(h),notes=[];
 notes.push(`${h} · ${per==="day"?"daytime":per}`);
 if(hfOf(h)>=21.5||hfOf(h)<7)notes.push("Mrs. Cohen is asleep");
 const o=ST.ledger.filter(l=>l.open).length;if(o)notes.push(o+" open favor"+(o>1?"s":""));
 $("#pipe").innerHTML=STEPS.map((s,k)=>`<div class="step ${k<n||(n===5&&k===5)?"done":""} ${k===n&&n<5?"on":""}"><b>${k<n||n===5&&k===5?IC.check.replace("<svg",'<svg width="12" height="12"'):k+1}</b>${s[1]}</div>`).join("")+`<div class="note">${notes.join(" · ")}</div>`;
 const ph=$("#aphase");if(ph)ph.textContent=n<0?"Waiting for your request":n>=5?"✓ All done":"Step "+(n+1)+" of 6 · "+STEPS[n][1]}
const urgCls=u=>/high|urgent|asap|now/i.test(u||"")?"hi":/low|whenever|no rush/i.test(u||"")?"lo":"";
function renderReq(){const el=$("#req");if(!el)return;const p=PARSE;
 if(!p){el.innerHTML=`<div class="rq empty">${mode==="play"?"Waiting for a request. Ask NearMind for something, or tap ⚡ Ask on a neighbor's phone.":"Waiting for a neighbor to ask…"}</div>`;return}
 const inc=p.requester&&p.requester!=="Maya";
 el.innerHTML=`<div class="rq"><div class="rqh"><span class="eyebrow ${inc?"inc":""}">${inc?"Incoming ask · "+esc(p.requester):"Request · Maya"}</span><span class="urg ${urgCls(p.urgency)}">${esc(p.urgency||"")}</span></div><div class="item">${esc(p.item)}</div><div class="qty">${esc(p.qty||"")} <span class="rqt" id="rqt">${CLOSED_AT&&T0?"✓ closed in "+fmtDur((CLOSED_AT-T0)/1000):T0?"⏱ "+fmtDur((Date.now()-T0)/1000):""}</span></div>${(p.substitutes||[]).length?`<div class="chips">${p.substitutes.map(s=>`<span class="chip">${esc(s)}</span>`).join("")}</div>`:""}</div>`}
function renderNst(){const el=$("#nst");if(!el)return;
 el.innerHTML=[2,3,4].map(k=>{const s=STAT[k]||"idle";return `<div class="np ${s}"><i></i><span>${PEOPLE[k-1].n}</span><span>${LAB[s]||s}</span></div>`}).join("")}
function logHTML(l){return `<div class="lg ${esc(l.kind)}"><div class="k">${KIND[l.kind]||"Note"} · ${esc(l.title)}<time>${esc(l.time||"")}</time></div>${l.html}</div>`}
const empty=(a,b)=>`<div class="empty-s"><b>${a}</b>${b}</div>`;
function renderTab(){const el=$("#tb");if(!el)return;
 $$(".t2").forEach(b=>b.classList.toggle("on",b.dataset.t===TAB));
 const o=ST.ledger.filter(l=>l.open).length,n=$("#nled");if(n){n.textContent=o;n.classList.toggle("hot",o>0)}
 let h="";
 if(TAB==="log")h=LOGS.length?LOGS.map(logHTML).join(""):empty("Decisions show up here","Every routing choice, translation and safety call NearMind makes is logged as it happens.");
 else if(TAB==="ledger")h=ST.ledger.length?[...ST.ledger].reverse().map(l=>{const nm=PEOPLE[l.frm-1].n,lend=l.kind==="lend";
  return `<div class="card"><div class="ch"><b>${esc(l.item)}</b><span class="tagc ${l.open?"open":"closed"}">${l.open?(lend?"return it":"say thanks"):(lend?"returned":"thanked")}</span></div><div class="sub">${lend?"Borrowed from":"Given by"} ${nm} · ${esc(l.since)}${l.done?" · settled "+esc(l.done):""}</div>${l.open&&mode==="play"?`<button class="go" data-settle="${l.id}">${lend?"I returned it ✓":"I said thanks ✓"}</button>`:""}</div>`}).join(""):empty("No favors yet","Borrowed items and thank-yous owed are tracked here, so nothing gets forgotten and nobody gets taken for granted.");
 else if(TAB==="nb")h=[2,3,4].map(k=>{const p=presence(k),a=ST.asks[k]||0;
  return `<div class="card"><div class="ch"><div class="av" style="background:${PEOPLE[k-1].c};width:28px;height:28px;font-size:13px">${PEOPLE[k-1].n[0]}</div><div><b>${PEOPLE[k-1].n}</b><div class="sub">${esc(p.t)}</div></div></div><div class="chips facts">${KNOWN[k].map(f=>`<span class="chip k">${esc(f)}</span>`).join("")}${(ST.learned[k]||[]).map(f=>`<span class="chip n">✦ ${esc(f)}</span>`).join("")}</div><div class="fair">Asked ${a}×${a?` <span style="margin-left:4px">${"<i></i>".repeat(Math.min(a,8))}</span>`:""}</div>${(()=>{const kk=karma(k),tot=kk.gave+kk.got;return `<div class="karma"><span>Helped you <b>${kk.gave}×</b></span><div class="kb"><i style="width:${tot?kk.gave/tot*100:50}%"></i></div><span>You helped <b>${kk.got}×</b></span></div>`})()}</div>`}).join("")+`<div class="sub" style="text-align:center;padding:2px">✦ = learned in conversation. NearMind balances who it asks so nobody is always the go-to.</div>`;
 else{const by={};ST.history.forEach(x=>{const n=x.req&&x.req!=="Maya"?"Maya":x.who;if(n&&n!=="nobody")by[n]=(by[n]||0)+1});
  h=ST.history.length?`<div class="hsum">${ST.history.length} closed · ${Object.entries(by).map(([n,c])=>`${esc(n)} helped ${c}×`).join(" · ")||"no helpers yet"}</div>`+[...ST.history].reverse().map(x=>`<div class="hrow">${IC.check}<div><b>${esc(x.item)}</b> <span>${x.req&&x.req!=="Maya"?esc(x.req)+" ← Maya":"Maya ← "+esc(x.who)}</span></div><time>${esc(x.at)}</time></div>`).join(""):empty("Nothing closed yet","Finished requests land here with who helped and when.");}
 const keep=TAB==="log"&&el.scrollHeight-el.scrollTop-el.clientHeight<60;
 el.innerHTML=h;if(TAB==="log"&&(keep||true))el.scrollTop=el.scrollHeight}
$("#grid").addEventListener("click",e=>{
 const t=e.target.closest(".t2");if(t){TAB=t.dataset.t;renderTab();return}
 const s=e.target.closest("[data-settle]");if(s){const l=ST.ledger.find(x=>x.id==s.dataset.settle);if(l){const nm=PEOPLE[l.frm-1].n;send(l.kind==="lend"?`I returned the ${l.item} to ${nm} ✓`:`I said thanks to ${nm} for the ${l.item}`)}return}
 const a=e.target.closest("[data-ask]");if(a){const p=$("#pop"+a.dataset.ask);const was=p.classList.contains("show");$$(".pop").forEach(x=>x.classList.remove("show"));!was&&p.classList.add("show");return}
 const q=e.target.closest("[data-sendas]");if(q){$$(".pop").forEach(x=>x.classList.remove("show"));send(q.textContent,+q.dataset.sendas);return}
 const sg=e.target.closest("#sug button,.starter[data-q]");if(sg){send(sg.dataset.q);return}
 if(e.target.closest("#dg")){digest();return}
 if(e.target.closest("#ex")){exportChat();return}
 if(!e.target.closest(".pop"))$$(".pop").forEach(x=>x.classList.remove("show"))});
$("#grid").addEventListener("submit",e=>{
 const af=e.target.closest("[data-askform]");if(af){e.preventDefault();const i=$("input",af),v=i.value.trim();if(!v)return;i.value="";$$(".pop").forEach(x=>x.classList.remove("show"));send(v,+af.dataset.askform);return}
 if(e.target.id==="f"){e.preventDefault();const i=$("#in"),v=i.value;i.value="";i.style.height="";send(v)}});
$("#grid").addEventListener("keydown",e=>{if(e.target.id==="in"&&e.key==="Enter"&&!e.shiftKey){e.preventDefault();$("#f").requestSubmit()}});
$("#grid").addEventListener("input",e=>{if(e.target.id==="in"){e.target.style.height="auto";e.target.style.height=Math.min(96,e.target.scrollHeight)+"px"}});
function renderClock(){const el=$("#clk");if(!el)return;const h=curLabel(),n=periodOf(h)==="night";
 el.innerHTML=(n?IC.moon:IC.sun)+h+(ST.clock.sim?" · simulated":"");
 const st=$("#street");if(st)st.dataset.p=periodOf(h);const ap=$("#apt");if(ap)ap.dataset.p=periodOf(h);window.NMApt&&NMApt.env({period:periodOf(h)})}
function renderPres(){[1,2,3,4].forEach(k=>{const p=presence(k),a=$("#av"+k),s=$("#pr"+k);if(a)a.className="av pres-"+p.c;if(s)s.textContent=p.t});mapState()}
function mapState(){[2,3,4].forEach(k=>{const h=$("#h"+k);if(!h)return;h.setAttribute("class","house st-"+(STAT[k]||"idle"))});
 const night=["night","evening"].includes(periodOf(curLabel()));
 [1,2,3,4].forEach(k=>{const h=$("#h"+k);if(h)h.classList.toggle("lit",night&&presence(k).c==="on"||k===1&&night)});
 [2,3,4].forEach(k=>{const u=$("#u"+k);if(!u)return;const s=STAT[k]||"idle",pr=presence(k).c;u.className="unit st-"+s+(pr==="sleep"?" sleep":"")+(night&&pr==="on"?" lit":"");const t=$("#ust"+k);if(t)t.textContent=pr==="sleep"&&s==="idle"?"asleep":(LAB[s]||s)});
 const u1=$("#u1");if(u1)u1.className="unit"+(night?" lit":"");
 if(window.NMApt){const o={};[1,2,3,4].forEach(k=>{const pr=presence(k).c;o[k]={status:k>1?(STAT[k]||"idle"):"idle",sleep:pr==="sleep",lit:night&&pr==="on"}});NMApt.status(o)}}
function ctxBar(){const el=$("#ctx");
 if(mode==="show")el.innerHTML=`<span class="sp-l">Scenario</span>`+Object.keys(SC).map(k=>`<button class="chip-b${k===cur?" on":""}" data-k="${k}">${SC[k].label}</button>`).join("");
 else el.innerHTML=`<span class="sp-l">Time of day</span>`+[["auto","Now"],["08:05","Morning"],["13:00","Midday"],["19:20","Evening"],["02:10","2 AM"]].map(([v,l])=>`<button class="chip-b${(v==="auto"&&!ST.clock.sim)||(ST.clock.sim&&ST.clock.label===v)?" on":""}" data-clk="${v}">${l}</button>`).join("")}
$("#ctx").onclick=async e=>{
 const k=e.target.closest("[data-k]");if(k){cur=k.dataset.k;reset();return}
 const c=e.target.closest("[data-clk]");if(c){try{ST={...ST,...await (await F("/api/clock",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({time:c.dataset.clk})})).json()}}catch(x){}ctxBar();renderAll()}};

/* ---------------- map animation ---------------- */
const HP={1:[55,72],2:[160,72],3:[265,72],4:[370,72]},HUB=[210,32];
function fly(a,b,col,node,D=650,svgEl){const svg=svgEl||$("#map");if(!svg)return;svg.append(node);const t0=performance.now();
 (function f(t){const k=Math.min(1,(t-t0)/D),e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
  node.setAttribute(node.tagName==="text"?"x":"cx",a[0]+(b[0]-a[0])*e);node.setAttribute(node.tagName==="text"?"y":"cy",a[1]+(b[1]-a[1])*e);
  node.setAttribute("opacity",k<.85?1:(1-k)/.15);k<1?requestAnimationFrame(f):node.remove()})(t0)}
function ping(ph,who){aptPing(ph,who);const svg=$("#map");if(!svg)return;const c=document.createElementNS(NS,"circle");c.setAttribute("r",4.5);c.setAttribute("fill",who==="ai"?"#35d6a4":PEOPLE[ph-1].c);
 const h=HP[ph];who==="ai"?fly(HUB,h,0,c):fly(h,HUB,0,c);const l=$("#l"+ph);l&&(l.classList.add("hot"),setTimeout(()=>l.classList.remove("hot"),800))}
function parcel(frm){window.NMApt&&NMApt.parcel(frm);const t=document.createElementNS(NS,"text");t.setAttribute("class","pkg");t.textContent="📦";fly([HP[frm][0],132],[HP[1][0],132],0,t,1500)}

/* ---------------- chat ---------------- */
function typingEl(ph,cls,label){const c=$("#c"+ph);if(!c)return;$$(".typing",c).forEach(x=>x.remove());const t=document.createElement("div");t.className="typing "+(cls||"");t.innerHTML=`${label||(ph===1?"NearMind is working":PEOPLE[ph-1].n+" is typing")} <b></b><b></b><b></b>`;c.append(t);c.scrollTop=c.scrollHeight;aptTyp(ph,true)}
const clearTyping=ph=>{$$("#c"+ph+" .typing").forEach(x=>x.remove());aptTyp(ph,false)};
let lastWho={};
function bubble(ph,who,text){const c=$("#c"+ph);if(!c)return;clearTyping(ph);pn++;
 if(ph===1)$$("#c1 .hint").forEach(x=>x.remove());
 const d=document.createElement("div"),fresh=lastWho[ph]!==who;lastWho[ph]=who;
 d.className="m "+who+(fresh?" fresh":"");
 d.innerHTML=(who==="ai"?`<div class="w">NearMind<em>${ph===1?"to Maya":"in "+PEOPLE[ph-1].style+" style"}</em></div>`:"")+`<div class="bd">${fmt(text)}</div><div class="t">${stamp()}${who==="me"?'<span class="k">✓✓</span>':""}</div>`;
 c.append(d);c.scrollTop=c.scrollHeight;ping(ph,who);aptSay(ph,who,text);blip(who);
 if(innerWidth<=860&&mpane!==ph){unread[ph]=true;setPane(mpane)}}
function toast(t){const d=document.createElement("div");d.className="toast";d.textContent=t;document.body.append(d);setTimeout(()=>d.remove(),2600)}

/* ---------------- sounds + connection watchdog ---------------- */
let SND="on",AC=null;try{SND=localStorage.getItem("nm.snd")||"on"}catch(e){}
function blip(kind){if(SND!=="on")return;
 try{AC=AC||new (window.AudioContext||window.webkitAudioContext)();if(AC.state==="suspended")AC.resume();
  const t=AC.currentTime,o=AC.createOscillator(),g=AC.createGain();
  o.type="sine";o.frequency.value=kind==="ai"?690:540;
  g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(.07,t+.012);g.gain.exponentialRampToValueAtTime(.0008,t+.17);
  o.connect(g);g.connect(AC.destination);o.start(t);o.stop(t+.2)}catch(e){}}
function drawSnd(){const b=$("#snd");if(b)b.textContent=SND==="on"?"🔔":"🔕";if(b)b.title=SND==="on"?"Message sounds on":"Message sounds off"}
let NET=true;
async function netCheck(){
 try{await fetch("/api/config",{cache:"no-store"});
  if(!NET){NET=true;document.body.classList.remove("offline");toast("Reconnected ✓");await loadState();renderAll()}}
 catch(e){if(NET){NET=false;document.body.classList.add("offline")}}}
setInterval(netCheck,4000);

/* ---------------- brain updates ---------------- */
function applyBrain(b){
 if(b.parse){PARSE={item:b.parse.item,qty:b.parse.qty,urgency:b.parse.urgency,substitutes:b.parse.substitutes||[],requester:b.parse.requester||"Maya"};
  if(!b.status&&(b.parse.item)){STAT={2:"",3:"",4:""}}
  if(!T0||CLOSED_AT){T0=Date.now();CLOSED_AT=0}
  renderReq()}
 if(b.status){Object.assign(STAT,b.status);renderNst();mapState()}
 if(b.phase){PHASE=b.phase;if(b.phase==="closed")onClosed()}
 (b.log||[]).forEach(l=>LOGS.push({kind:l.kind||"route",title:l.title||"",html:l.html!=null?l.html:esc(l.text||""),time:stamp()}));
 renderPipe();renderTab()}
function setBusy(b){busy=b;window.NMApt&&NMApt.busy(b);document.body.classList.toggle("live-busy",b);const m=$("#mind");m&&m.classList.toggle("busy",b);const i=$("#inp");i&&i.classList.toggle("off",b);
 const c=$("#c1");if(c){$$(".typing.nm",c).forEach(x=>x.remove());if(b)typingEl(1,"nm")}}
function finish(){setBusy(false);const l=$("#live");l&&(l.textContent="");["1","2","3","4"].forEach(clearTyping);
 if(pendingQ){$("#c1").append(pendingQ);$("#c1").scrollTop=1e9;pendingQ=null}const x=$("#in");x&&x.focus();renderPipe()}
function handle(e){seen=Math.max(seen,e.id||0);
 if(e.t==="reset"||e.t==="done"&&false)return;
 if(e.t==="done"){finish();return}
 if(!busy)setBusy(true);
 if(e.t==="msg"){$$(".qr").forEach(x=>x.remove());bubble(e.ph,e.who,e.text);if(e.ph===1||busy)typingEl(1,"nm")}
 else if(e.t==="typing"){typingEl(e.ph,"r")}
 else if(e.t==="brain")applyBrain(e);
 else if(e.t==="memory"){ST.learned=e.learned;renderTab();renderPipe()}
 else if(e.t==="ledger"){const had=ST.ledger.length;ST.ledger=e.ledger;if(e.ledger.length>had)parcel(e.ledger[e.ledger.length-1].frm);renderTab();renderPipe()}
 else if(e.t==="history"){ST.history=e.history;renderTab()}
 else if(e.t==="step"){const l=$("#live");if(l)l.textContent=e.text}
 else if(e.t==="quick"){const q=document.createElement("div");q.className="qr";e.options.forEach(o=>{const b=document.createElement("button");b.textContent=o;b.onclick=()=>send(o);q.append(b)});pendingQ=q}
 else if(e.t==="error"){const x=document.createElement("div");x.className="err";x.textContent="Something went wrong: "+e.error;$("#c1").append(x)}}
const F=(u,o={})=>fetch(u,PUB?{...o,headers:{...(o.headers||{}),"X-Sid":SID}}:o);
const SID=(()=>{try{let v=localStorage.getItem("nm.sid");if(!v){v=Math.random().toString(36).slice(2)+Date.now().toString(36);localStorage.setItem("nm.sid",v)}return v}catch(e){return Math.random().toString(36).slice(2)}})();
let LLM=true,FRIENDS_ON=false;fetch("/api/config").then(r=>r.json()).then(c=>{PUB=!!c.public;if(PUB)document.body.classList.add("pub");LLM=c.llm!==false;NB=c.neighbors||{};FRIENDS_ON=!!c.friends;document.body.classList.toggle("nollm",!LLM)}).catch(()=>{});
async function loadState(){try{const s=await (await F("/api/state")).json();ST={...ST,clock:s.clock,learned:s.learned,ledger:s.ledger,history:s.history,asks:s.asks};ST.clock.label=ST.clock.label||realLabel()}catch(e){}}
async function send(text,from=1){text=(text||"").trim();if(!text||busy)return;if(mode!=="play"){toast("Switch to Live to chat with NearMind");return}
 setBusy(true);streaming=true;if(mode==="play"&&STAGE==="talk")setStage("build");
 try{const r=await F("/api/turn",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({text,from})});
  const rd=r.body.getReader(),dec=new TextDecoder();let buf="";
  while(true){const{value,done}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});let k;
   while((k=buf.indexOf("\n"))>=0){const line=buf.slice(0,k);buf=buf.slice(k+1);if(line.trim())handle(JSON.parse(line))}}
 }catch(err){const x=document.createElement("div");x.className="err";x.textContent="Can't reach the NearMind server right now — reconnecting automatically, then just send again.";$("#c1").append(x);finish();netCheck()}
 streaming=false;await loadState();ctxBar();renderTab();renderPres()}
async function poll(){if(mode!=="play"||streaming)return;
 try{const j=await (await F("/api/log?since="+seen)).json();let ev=j.events;
  const ri=ev.map(e=>e.t).lastIndexOf("reset");if(ri>=0)ev=ev.slice(ri+1);
  ev.forEach(handle);if(!ev.length)seen=Math.max(seen,j.last);
  if(!j.busy&&busy&&!ev.length)finish()}catch(e){}}
setInterval(poll,1800);

/* ---------------- showcase player ---------------- */
function apply(ev){const[ph,who,t,b]=ev;bubble(ph,who,t);
 if(b){const o={};
  if(b.parse)o.parse={item:b.parse.item,qty:b.parse.qty,urgency:b.parse.urg,substitutes:b.parse.subs,requester:b.parse.req};
  if(b.status)o.status=b.status;if(b.phase)o.phase=b.phase;
  if(b.log)o.log=[{kind:b.log[0],title:b.log[1],html:b.log[2]}];
  applyBrain(o);
  if(b.mem)for(const k in b.mem){ST.learned[k]=[...(ST.learned[k]||[]),...b.mem[k]];renderTab()}
  if(b.ledger){b.ledger.forEach(l=>ST.ledger.push({id:ST.ledger.length+1,item:l.item,frm:l.frm,kind:l.kind,open:true,since:stamp()}));parcel(b.ledger[0].frm);renderTab();renderPipe()}
  if(b.phase==="closed"){const w=Object.keys(STAT).find(k=>STAT[k]==="won");ST.history.push({item:PARSE?PARSE.item:"?",who:w?PEOPLE[w-1].n:"nobody",req:PARSE&&PARSE.requester,at:stamp()});renderTab()}
  if(b.status)[2,3,4].forEach(k=>{if(b.status[k]==="asked")ST.asks[k]=(ST.asks[k]||0)+1})}
 $("#bar").style.width=((i+1)/SC[cur].ev.length*100)+"%"}
async function typingStep(ev,id){const[ph,who,t]=ev;typingEl(ph,who==="me"?"r":"",who==="ai"?"NearMind is typing":PEOPLE[ph-1].n+" is typing");await wait(550+Math.min(t.length*9,1200));clearTyping(ph);return id===run}
async function loop(){const id=++run,evs=SC[cur].ev;
 while(i<evs.length&&!paused&&id===run){const ev=evs[i];if(!await typingStep(ev,id))return;if(paused||id!==run)return;apply(ev);i++;await wait(520)}
 if(i>=evs.length)$("#pp").textContent="Done"}
function reset(){run++;i=0;paused=false;pn=0;lastWho={};T0=0;CLOSED_AT=0;DUR=[];$("#pp").textContent="Pause";$("#bar").style.width="0";
 PARSE=null;PHASE=null;STAT={2:"",3:"",4:""};LOGS=[];ST={clock:{label:SC[cur].clock,sim:true},learned:{2:[],3:[],4:[]},ledger:[],history:[],asks:{2:0,3:0,4:0}};
 build();ctxBar();loop()}
$("#pp").onclick=()=>{if(i>=SC[cur].ev.length)return;paused=!paused;$("#pp").textContent=paused?"Play":"Pause";if(!paused)loop();else{run++;$$(".typing").forEach(x=>x.remove())}};
$("#step").onclick=()=>{if(i>=SC[cur].ev.length)return;if(!paused){paused=true;run++;$("#pp").textContent="Play"}$$(".typing").forEach(x=>x.remove());apply(SC[cur].ev[i]);i++};
$("#sp").onclick=()=>{speed=speed===1?2:speed===2?4:1;$("#sp").textContent=speed+"x"};
$("#re").onclick=reset;

/* ---------------- modes ---------------- */
const DEFN=PEOPLE.map(p=>({n:p.n,role:p.role}));let NB={};
function applyNames(m){PEOPLE.forEach((p,i)=>{const r=m==="play"&&NB[i+1];p.n=r?r:DEFN[i].n;p.role=r?DEFN[i].role.replace(/^Neighbor/,"Real neighbor"):DEFN[i].role})}
async function setMode(m,fresh){applyNames(m);let hasEv=false;mode=m;run++;busy=false;pendingQ=null;streaming=false;pn=0;lastWho={};
 $$("#modes button").forEach(t=>t.classList.toggle("on",t.dataset.m===m));
 const show=m==="show";$("#ctl").style.display=show?"":"none";$("#nw").style.display=$("#rw").style.display=$("#wab").style.display=show?"none":"";
 $("#bar").style.width="0";PARSE=null;PHASE=null;STAT={2:"",3:"",4:""};LOGS=[];

 if(show){document.body.dataset.stage="show";const v=$("#vw");v&&(v.style.display="none");reset();return}
 ST={clock:{label:realLabel(),sim:false},learned:{2:[],3:[],4:[]},ledger:[],history:[],asks:{2:0,3:0,4:0}};
 await loadState();build();ctxBar();
 if(fresh){try{const r=await (await F("/api/reset",{method:"POST",headers:{"content-type":"application/json"},body:"{}"})).json();seen=r.last;hasEv=false}catch(e){}}
 else{seen=0;try{const j=await (await F("/api/log?since=0")).json();let ev=j.events;const ri=ev.map(e=>e.t).lastIndexOf("reset");if(ri>=0)ev=ev.slice(ri+1);hasEv=ev.length>0;REPLAY=true;ev.forEach(handle);REPLAY=false;seen=j.last;if(!j.busy&&busy)finish()}catch(e){REPLAY=false}}
 await loadState();renderAll();setStage(hasEv?"build":"talk");const x=$("#in");x&&x.focus();waPoll()}
$("#vw").onclick=()=>setStage(STAGE==="detail"?"build":"detail");
$("#nw").onclick=()=>{if(!busy)setMode("play",true)};
$("#rw").onclick=async()=>{if(busy||!confirm("Forget everything NearMind has learned (memory, favors, history)?"))return;try{await F("/api/reset",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({world:true})})}catch(e){}setMode("play",true)};
$("#modes").onclick=e=>{const m=e.target.dataset.m;m&&m!==mode&&setMode(m)};
document.addEventListener("keydown",e=>{if(e.key==="Escape"){$$(".pop").forEach(x=>x.classList.remove("show"));$("#wap").classList.remove("show")}
 if(e.key==="/"&&mode==="play"&&!["INPUT","TEXTAREA"].includes(document.activeElement?.tagName)){e.preventDefault();const x=$("#in");x&&x.focus()}
 if(mode==="show"&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!["INPUT","TEXTAREA","SELECT"].includes(document.activeElement?.tagName)){
  const k=e.key.toLowerCase(),map={" ":"#pp",arrowright:"#step",r:"#re",s:"#sp"};
  if(map[k]){e.preventDefault();const bt=$(map[k]);bt&&bt.click()}}});
[["#pp","Pause / play (Space)"],["#step","Step one message (→)"],["#re","Replay scenario (R)"],["#sp","Playback speed (S)"]].forEach(([q,t])=>{const el=$(q);if(el)el.title=t});
$("#snd").onclick=()=>{SND=SND==="on"?"off":"on";try{localStorage.setItem("nm.snd",SND)}catch(e){}drawSnd();if(SND==="on")blip("ai")};
drawSnd();
let THM="light";try{THM=localStorage.getItem("nm.theme")||"light"}catch(e){}
function drawThm(){document.documentElement.dataset.theme=THM;const b=$("#thm");if(b){b.textContent=THM==="dark"?"☀️":"🌙";b.title=THM==="dark"?"Switch to light theme":"Switch to dark theme"}}
$("#thm").onclick=()=>{THM=THM==="dark"?"light":"dark";try{localStorage.setItem("nm.theme",THM)}catch(e){}drawThm()};
drawThm();

/* ---------------- WhatsApp panel ---------------- */
let waS={},waF=[],waN={neighbors:{},slots:{}},REALST={};
const fmtPhone=n=>{n=String(n||"");return n.startsWith("966")&&n.length===12?"+966 "+n.slice(3,5)+" "+n.slice(5,8)+" "+n.slice(8):"+"+n};
function renderReal(){[2,3,4].forEach(k=>{const b=$("#rb"+k);if(!b)return;const r=mode==="play"&&REALST[k];b.hidden=!r;if(!r)return;
 const [t,c,tip]=r.held?["🌙 Held till 08:00","held","It's quiet hours: NearMind will send at 08:00. Send /send in WhatsApp to send now."]
  :r.waiting?["⏳ Awaiting reply","wait","NearMind asked "+r.name+" and is waiting for their answer"]
  :r.joined?["✓ Real · joined","ok","A real neighbor on WhatsApp. NearMind can ask them for favors."]
  :["Real · not joined yet","no","Ask "+r.name+" to send any message to your number first"];
 b.textContent=t;b.className="rb "+c;b.title=tip;b.onclick=()=>{$("#wap").classList.add("show");waPoll()}});
 if(window.NMApt){const C={ok:["#dcf6e5","#1a7a45","#a8e2c0"],wait:["#fff1d6","#b0630f","#f0c98a"],held:["#e8ebff","#3b46a0","#c3c9f5"],no:["#f3f4f4","#5b6b65","#d9dfdc"]},m={};
  [2,3,4].forEach(k=>{const r=mode==="play"&&REALST[k];if(!r){m[k]={real:null};return}
   const [t,c]=r.held?["🌙 Held till 08:00","held"]:r.waiting?["⏳ Awaiting reply","wait"]:r.joined?["✓ Real neighbor · joined","ok"]:["Real · not joined yet","no"];
   m[k]={real:{t,bg:C[c][0],fg:C[c][1],bd:C[c][2],pulse:c==="wait"}}});NMApt.status(m)}}
async function realPoll(){if(mode!=="play"||document.hidden)return;try{const s=await (await F("/api/state")).json();REALST=s.real||{};renderReal()}catch(e){}}
setInterval(realPoll,5000);
async function waPoll(){if(mode!=="play")return;try{waS=await (await fetch("/api/wa/status")).json()}catch(e){waS={state:"bridge_off"}}
 try{waF=(await (await fetch("/api/wa/friends")).json()).numbers||[]}catch(e){waF=[]}
 try{waN=await (await fetch("/api/wa/neighbors")).json()}catch(e){waN={neighbors:{},slots:{}}}waRender()}
setInterval(waPoll,3000);
const post=(u,b)=>fetch(u,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(b)});
function waRender(){const b=$("#wab"),p=$("#wap"),s=waS.state||"bridge_off";
 b.innerHTML=`<i class="wdot" style="background:${s==="open"||waS.cloud?"#25d366":s==="pairing"?"#e0a96d":"#55626c"}"></i>WhatsApp`;
 let h="";
 if(s==="open")h=`<b>Connected ✓</b><p>NearMind chats in your WhatsApp "Message yourself" chat (+${esc(waS.phone)}). Type there as Maya and it answers.</p><label class="sw"><input type="checkbox" id="mir" ${waS.mirror?"checked":""}> NearMind answers me on WhatsApp</label><label class="sw"><input type="checkbox" id="nbs" ${waS.neighbors_shown?"checked":""}> Also show its chats with neighbors</label><p>Off = private: your chat shows only you and NearMind.</p>${FRIENDS_ON?`<hr><b>Friends who agreed</b><p>They message your number first and NearMind only answers them. They can send <i>stop</i> any time. It never starts a chat.</p><div>${waF.filter(n=>!Object.values(waN.neighbors||{}).some(v=>v.number===n)).map(n=>`<div class="fr">+${esc(n)}<button data-rm="${esc(n)}">remove</button></div>`).join("")||'<p>No friends added yet.</p>'}</div><form id="ff" class="ffm"><input id="fn" placeholder="+966 5x xxx xxxx"><button>Add</button></form>`:""}`;
 if(s==="open"){const sl=waN.slots||{},nb=waN.neighbors||{};
  h+=`<hr><b>Real neighbors</b><p>Put a real person in a neighbor slot. They message your number once to join (any text), then NearMind asks them for favors on WhatsApp and their real replies drive it. They can send <i>stop</i> any time.</p>`+
  ["2","3","4"].map(k=>nb[k]?`<div class="fr nbr"><span class="nbav">${esc(nb[k].name[0]||"?")}</span><span><b>${esc(nb[k].name)}</b> <small class="${(REALST[k]||{}).joined?"jn":"nj"}">${(REALST[k]||{}).joined?"✓ joined":"not joined yet"}</small><br><small>${esc(fmtPhone(nb[k].number))} · Apartment #${10+(+k)*2-2}</small></span><button data-nbrm="${k}" aria-label="Remove ${esc(nb[k].name)}">remove</button></div>`
   :`<form class="nbf" data-slot="${k}"><small>Apartment #${10+(+k)*2-2} · now AI ${esc(sl[k]||"")}</small><input name="name" placeholder="Name" maxlength="40" required aria-label="Neighbor name"><input name="number" placeholder="+966 5x xxx xxxx" inputmode="tel" required aria-label="WhatsApp number with country code"><button>Add</button></form>`).join("")}
 else if(s==="pairing"&&waS.code)h=`<b>Link your WhatsApp</b><div class="code">${esc(waS.code.slice(0,4))}-${esc(waS.code.slice(4))}</div><p>On your phone: WhatsApp → Settings → Linked devices → Link a device → <b>Link with phone number instead</b> → type this code.</p>`;
 else if(s==="bridge_off")h=`<b>Bridge not running</b><p>Run <code>start-whatsapp.bat</code> in the nearmind folder.</p>`;
 else if(s==="logged_out")h=`<b>Logged out</b><p>Delete the <code>bridge/auth</code> folder and restart the bridge to link again.</p>`;
 else h=`<b>${esc(s)}…</b><p>One moment.</p>`;
 h+=`<hr><b>Meta Cloud test number ${waS.cloud?"✓":"— not set up"}</b><p>${waS.cloud?"Configured. Friends you verified in the Meta dashboard can message the test number and NearMind replies from it. Webhook: <code>/api/wa/cloud</code>. Free text works for 24h after they write; otherwise use a template.":"Add <code>META_TOKEN</code>, <code>META_PHONE_ID</code> and <code>META_APP_SECRET</code> to <code>.env</code> and restart, then point Meta's webhook at <code>/api/wa/cloud</code>."}</p>`;
 if(p.dataset.h!==h){p.innerHTML=h;p.dataset.h=h;const m=$("#mir");m&&(m.onchange=()=>post("/api/wa/mirror",{on:m.checked}));const nb=$("#nbs");nb&&(nb.onchange=()=>post("/api/wa/mirror",{neighbors:nb.checked}));
  const ff=$("#ff");ff&&(ff.onsubmit=async e=>{e.preventDefault();const v=$("#fn").value;if(v.replace(/\D/g,"").length<8)return;await post("/api/wa/friends",{add:v});waPoll()});
  $$("[data-rm]",p).forEach(x=>x.onclick=async()=>{await post("/api/wa/friends",{remove:x.dataset.rm});waPoll()});
  $$(".nbf",p).forEach(f=>f.onsubmit=async e=>{e.preventDefault();nbChanged(await (await post("/api/wa/neighbors",{slot:+f.dataset.slot,name:f.name.value,number:f.number.value})).json())});
  $$("[data-nbrm]",p).forEach(x=>x.onclick=async()=>{if(!confirm("Remove this real neighbor? The slot goes back to the AI neighbor."))return;nbChanged(await (await post("/api/wa/neighbors",{slot:+x.dataset.nbrm,remove:true})).json())})}}
async function nbChanged(r){if(r&&r.error){toast(r.error);return}if(r&&r.neighbors){NB={};Object.entries(r.neighbors).forEach(([k,v])=>NB[k]=v.name)}
 toast("Neighbors updated");await waPoll();if(mode==="play"&&!busy){$("#wap").classList.remove("show");setMode("play")}}
$("#wab").onclick=()=>{$("#wap").classList.toggle("show");waPoll()};

function labelBtns(){const nr=innerWidth<=600,nw=$("#nw"),rw=$("#rw");if(nw)nw.textContent=nr?"＋ New":"＋ New request";if(rw){rw.textContent=nr?"↺ Reset":"Reset world";rw.title="Forget everything: memory, ledger, history"}}
let rsz;addEventListener("resize",()=>{clearTimeout(rsz);rsz=setTimeout(()=>{labelBtns();const vw=$("#vw");if(vw&&vw.style.display!=="none"){const nr=innerWidth<=600,d=STAGE==="detail";vw.textContent=d?(nr?"🏢":"🏢 Apartment view"):(nr?"📊":"📊 Full dashboard")}},150)});
labelBtns();
/* ---------------- boot ---------------- */
setInterval(()=>{if(!ST.clock.sim){renderClock();renderPres()}},30000);
document.body.dataset.stage="show";
reset();
