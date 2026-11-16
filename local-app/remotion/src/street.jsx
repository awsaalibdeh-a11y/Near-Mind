// NearMind Street: the coach's sketch, animated. Robot on the roof, six apartments, every message travels the dashed spine.
// Driven live from the page through window.NMStreet (say / think / status / typing / asker / request / period / clear).
import React,{useEffect,useState} from "react";
import {createRoot} from "react-dom/client";
import {Player} from "@remotion/player";
import {AbsoluteFill,useCurrentFrame,spring,Easing,interpolate} from "remotion";

const W=1400,H=980,FPS=30,D=40;                       // D = frames a message takes to travel
const B={x:330,y:250,w:740,h:640};                    // building
const AW=290,AH=150,SX=700,ROOF={x:700,y:B.y};
const COLS={sedra:0,sulaiman:0,alwalid:0,osama:1,asma:1,anas:1};
const ROWS={sedra:0,osama:0,sulaiman:1,asma:1,alwalid:2,anas:2};
const AX=id=>COLS[id]?750:360, AY=id=>300+ROWS[id]*195;
const DOOR=id=>({x:COLS[id]?750:650,y:AY(id)+AH/2});
const PATH=id=>{const d=DOOR(id);return [d,{x:SX,y:d.y},{x:SX,y:ROOF.y}]};
const SKY={day:["#bfe3ff","#f1f9ff"],evening:["#ffc79a","#fdeee0"],"early morning":["#ffe0b5","#eef6ff"],night:["#16224d","#0a1022"]};
const PILL={asked:["asked","#fff1d6","#b0630f"],offer:["has it","#e2f1ff","#1f6fb8"],no:["can't","#eef1f0","#7c8a84"],
 chosen:["chosen ✓","#17c394","#fff"],released:["thanked","#eef6f2","#5f8f7b"]};

const store={s:{people:{},period:"day",busy:false,asker:null,req:null,think:null,packets:[],bubbles:{},status:{},typing:{},asleep:{},look:null,finale:null},subs:new Set(),ref:null,onPick:null};
const emit=()=>store.subs.forEach(f=>f());
const nowF=()=>{try{return store.ref.current.getCurrentFrame()}catch(e){return 0}};
function useStore(){const[,t]=useState(0);useEffect(()=>{const f=()=>t(x=>x+1);store.subs.add(f);return()=>store.subs.delete(f)},[])}
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const ease=Easing.inOut(Easing.cubic);

function along(pts,t){            // point at fraction t along a polyline
 const seg=[];let L=0;for(let i=1;i<pts.length;i++){const l=Math.hypot(pts[i].x-pts[i-1].x,pts[i].y-pts[i-1].y);seg.push(l);L+=l}
 let d=t*L;for(let i=0;i<seg.length;i++){if(d<=seg[i]||i===seg.length-1){const f=seg[i]?d/seg[i]:0;return{x:pts[i].x+(pts[i+1].x-pts[i].x)*f,y:pts[i].y+(pts[i+1].y-pts[i].y)*f}}d-=seg[i]}
 return pts[pts.length-1]}

function Dots({frame,color="#8a9a93"}){return <div style={{display:"flex",gap:5}}>{[0,1,2].map(i=><div key={i} style={{width:8,height:8,borderRadius:"50%",background:color,transform:"translateY("+(-Math.abs(Math.sin(frame/5+i*0.9))*6)+"px)"}}/>)}</div>}

function Robot({frame}){
 const s=store.s,bob=Math.sin(frame/22)*4;
 const last=s.packets.length?s.packets[s.packets.length-1]:null;
 const talking=last&&last.from==="robot"&&frame-last.f0>=0&&frame-last.f0<18;
 const heard=last&&last.to==="robot"&&frame-last.f0>=D&&frame-last.f0<D+14;
 const bounce=heard?Math.sin((frame-last.f0-D)/14*Math.PI)*-10:0;
 const look=s.look?{x:clamp((AX(s.look)+AW/2-SX)/90,-5,5),y:clamp((AY(s.look)-120)/160,-1,5)}:{x:Math.sin(frame/60)*2,y:0};
 const glow=s.busy?0.6+0.4*Math.sin(frame/4):0.25;
 const eye=(cx)=><g><circle cx={cx} cy={98} r={21} fill="#fff" stroke="#1f6f9e" strokeWidth={4}/>
  <circle cx={cx+look.x} cy={98+look.y} r={9} fill="#14303f"/>
  {s.busy&&<path d={`M${cx-7} ${98} a7 7 0 1 1 7 7`} stroke="#35d6a4" strokeWidth={3} fill="none" transform={`rotate(${frame*12} ${cx} 98)`}/>}</g>;
 return <svg width={W} height={260} style={{position:"absolute",left:0,top:0,transform:`translateY(${bob+bounce}px)`}}>
  <defs><radialGradient id="tip"><stop offset="0" stopColor="#7dffd5"/><stop offset="1" stopColor="#17c394" stopOpacity="0"/></radialGradient></defs>
  {[[640,40,612,12],[760,40,788,12]].map(([x1,y1,x2,y2],i)=><g key={i}><line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1f6f9e" strokeWidth={6} strokeLinecap="round"/>
   <circle cx={x2} cy={y2} r={16} fill="url(#tip)" opacity={glow}/><circle cx={x2} cy={y2} r={6} fill={s.busy?"#35d6a4":"#9fd8ee"}/></g>)}
  <rect x={590} y={38} width={220} height={120} rx={34} fill="#e9f6fb" stroke="#1f6f9e" strokeWidth={6}/>
  {eye(655)}{eye(745)}
  {talking?<ellipse cx={700} cy={135} rx={22} ry={8+Math.abs(Math.sin(frame/2))*6} fill="#1f6f9e"/>
   :<path d="M670 128 Q700 150 730 128" stroke="#1f6f9e" strokeWidth={6} fill="none" strokeLinecap="round"/>}
  <path d={`M560 ${B.y} L590 162 L810 162 L840 ${B.y} Z`} fill="#d4ecf6" stroke="#1f6f9e" strokeWidth={6} strokeLinejoin="round"/>
  <text x={700} y={212} textAnchor="middle" fontFamily="system-ui,Segoe UI,sans-serif" fontWeight={800} fontSize={20} letterSpacing={6} fill="#1f6f9e">NEARMIND</text>
 </svg>}

function Apartment({id,frame}){
 const s=store.s,p=s.people[id]||{name:id,apt:"",color:"#999",icon:"🏠"};
 const x=AX(id),y=AY(id),st=s.status[id],sale=s.req&&s.req.kind==="sale",pill=sale&&st==="offer"?["wants it","#e2f1ff","#1f6fb8"]:sale&&st==="chosen"?["buyer ✓","#17c394","#fff"]:PILL[st],sleep=s.asleep[id],asker=s.asker===id,typing=s.typing[id];
 const hot=s.packets.some(k=>(k.from===id||k.to===id)&&frame-k.f0>=0&&frame-k.f0<=D+10);
 const night=s.period==="night";
 const border=asker?"#ff7eb6":{asked:"#f2b560",offer:"#66b8ff",chosen:"#17c394",no:"#c9d2ce",released:"#b6c9bf"}[st]||"#1f6f9e";
 const bg=sleep?"linear-gradient(180deg,#46527e,#2c365a)":night?"linear-gradient(180deg,#fff2c9,#ffe3a1)":"linear-gradient(180deg,#ffffff,#f1f7fb)";
 const pulse=asker?4+Math.sin(frame/6)*4:0;
 return <div onClick={()=>store.onPick&&store.onPick(id)} style={{position:"absolute",left:x,top:y,width:AW,height:AH,cursor:"pointer"}}>
  <div style={{position:"absolute",left:10,top:-34,width:AW-20,height:34,background:sleep?"#3a4570":"#e8f3f8",border:"5px solid "+border,borderBottom:"none",clipPath:"polygon(4% 100%,12% 0,88% 0,96% 100%)"}}/>
  <div style={{position:"absolute",right:18,top:16+(hot?Math.sin(frame/4)*4:0),fontSize:30,zIndex:2,opacity:sleep?0.5:0.9}}>{p.icon}</div>
  <div style={{position:"absolute",inset:0,borderRadius:16,background:bg,border:"5px solid "+border,boxShadow:(asker?`0 0 0 ${pulse}px #ff7eb655,`:"")+(st==="chosen"?"0 0 0 8px #17c39433,":"")+"0 8px 22px rgba(20,40,32,.16)",
   padding:"14px 16px",boxSizing:"border-box",color:sleep?"#e8ecff":"#14201c",fontFamily:"system-ui,Segoe UI,sans-serif",display:"flex",flexDirection:"column",gap:6,opacity:st==="released"?0.8:1}}>
   <div style={{display:"flex",alignItems:"center",gap:12}}>
    <div style={{width:72,height:72,borderRadius:"50%",background:p.color,overflow:"hidden",flex:"none",boxShadow:`0 0 0 4px #fff,0 0 0 ${hot?7:4}px ${hot?border:"#fff"}`,filter:sleep?"grayscale(.5) brightness(.75)":"none",display:"grid",placeItems:"center",fontWeight:800,fontSize:28,color:"#0b1a14"}}>
     {p.img?<img src={p.img} alt="" style={{width:"100%",height:"100%",objectFit:"cover"}}/>:p.name[0]}</div>
    <div style={{lineHeight:1.15,minWidth:0}}><div style={{fontWeight:800,fontSize:27}}>{p.name}</div><div style={{fontSize:16,opacity:0.6,fontWeight:600}}>Apt {p.apt}</div></div>
   </div>
   <div style={{display:"flex",alignItems:"center",gap:8,marginTop:"auto",minHeight:28,paddingLeft:84}}>
    {asker&&<span style={{fontSize:14,fontWeight:800,letterSpacing:1,textTransform:"uppercase",background:"#ff7eb6",color:"#fff",borderRadius:999,padding:"4px 12px"}}>asking</span>}
    {!asker&&pill&&<span style={{fontSize:14,fontWeight:800,letterSpacing:1,textTransform:"uppercase",background:pill[1],color:pill[2],borderRadius:999,padding:"4px 12px"}}>{pill[0]}</span>}
    {!asker&&!pill&&sleep&&<span style={{fontSize:14,fontWeight:800,letterSpacing:1,textTransform:"uppercase",background:"#e4e8fb",color:"#5b6aa8",borderRadius:999,padding:"4px 12px"}}>asleep</span>}
    {typing&&<div style={{marginLeft:"auto",background:sleep?"#ffffff22":"#eef3f1",borderRadius:999,padding:"8px 12px"}}><Dots frame={frame}/></div>}
   </div>
   {sleep&&[0,1,2].map(i=><div key={i} style={{position:"absolute",right:20+i*15,top:50-((frame/2+i*14)%36)-i*5,fontWeight:800,fontSize:18+i*5,color:"#c9d3ff",opacity:0.9-i*0.25}}>z</div>)}
  </div>
 </div>}

function Bubble({id,frame}){
 const b=store.s.bubbles[id];if(!b||frame<b.f0)return null;
 const age=frame-b.f0,sp=spring({frame:age,fps:FPS,config:{damping:12,stiffness:160}});
 const p=store.s.people[id]||{name:id,color:"#999"},left=!COLS[id],fromRobot=b.from==="robot";
 const x=left?24:1076,y=AY(id)-10,w=300;
 const fade=interpolate(age,[FPS*11,FPS*14],[1,0],{extrapolateLeft:"clamp",extrapolateRight:"clamp"});if(fade<=0)return null;
 return <div style={{position:"absolute",left:x,top:y,width:w,opacity:sp*fade,transform:`translateX(${(1-sp)*(left?30:-30)}px) scale(${0.85+0.15*sp})`,transformOrigin:left?"right center":"left center",fontFamily:"system-ui,Segoe UI,sans-serif"}}>
  <div style={{background:"#fff",borderRadius:18,padding:"12px 15px",boxShadow:"0 10px 28px rgba(20,40,32,.18)",borderTop:"6px solid "+(fromRobot?"#17c394":p.color),position:"relative"}}>
   <div style={{fontSize:13,fontWeight:800,letterSpacing:1,textTransform:"uppercase",color:fromRobot?"#0b8f69":"#36424a",marginBottom:4}}>{fromRobot?"🤖 NearMind → "+p.name:p.name+" → 🤖 NearMind"}</div>
   <div style={{fontSize:19,lineHeight:1.32,color:"#14201c"}}>{b.text}</div>
   <div style={{position:"absolute",top:34,[left?"right":"left"]:-12,width:0,height:0,borderTop:"12px solid transparent",borderBottom:"12px solid transparent",[left?"borderLeft":"borderRight"]:"14px solid #fff"}}/>
  </div></div>}

// ---------- finale: the item travels door to door, camera zooms on the receiver's door, item lands on the doormat ----------
const F_TRAVEL=70,F_IN=[55,95],F_HOLD=165,F_OUT=36;
const FOOT=id=>({x:DOOR(id).x+(COLS[id]?-26:26),y:AY(id)+AH-14});
function zoomOf(frame){
 const fz=store.s.finale;if(!fz||frame<fz.f0)return{z:1,tx:0,ty:0,k:0};
 const t=frame-fz.f0,end=F_IN[1]+F_HOLD;
 let k=t<F_IN[0]?0:t<F_IN[1]?(t-F_IN[0])/(F_IN[1]-F_IN[0]):t<end?1:t<end+F_OUT?1-(t-end)/F_OUT:0;
 k=Easing.inOut(Easing.cubic)(clamp(k,0,1));
 const f=FOOT(fz.to),fx=f.x+(COLS[fz.to]?-60:60),fy=f.y-50,z=1+1.35*k;   // focus point eases to screen centre as we zoom
 return{z,tx:k*(W/2-fx*z),ty:k*(H/2-fy*z),k};
}
function Doors({frame}){
 const fz=store.s.finale,t=fz?frame-fz.f0:-1,night=store.s.period==="night";
 return <>{Object.keys(COLS).map(id=>{const d=DOOR(id),on=fz&&fz.to===id&&t>=F_IN[0]&&t<F_IN[1]+F_HOLD+F_OUT;
  return <div key={id} style={{position:"absolute",left:d.x-(COLS[id]?0:30),top:AY(id)+AH-64,width:30,height:60,borderRadius:"8px 8px 0 0",
   background:on?"#fff6d6":night?"#3a4570":"#d9ecf5",border:"4px solid "+(on?"#17c394":"#1f6f9e"),borderBottom:"none",
   boxShadow:on?`0 0 0 ${6+Math.sin(frame/4)*3}px #17c39444`:"none",zIndex:3}}>
   <div style={{position:"absolute",[COLS[id]?"left":"right"]:5,top:28,width:6,height:6,borderRadius:"50%",background:"#1f6f9e"}}/></div>})}</>}
function Finale({frame}){
 const fz=store.s.finale;if(!fz||frame<fz.f0)return null;
 const t=frame-fz.f0,end=F_IN[1]+F_HOLD+F_OUT;if(t>end+10)return null;
 const a=FOOT(fz.from),b=FOOT(fz.to),pts=[a,{x:SX,y:a.y},{x:SX,y:b.y},b];
 const raw=clamp(t/F_TRAVEL,0,1),pos=raw<1?along(pts,Easing.inOut(Easing.quad)(raw)):b;
 const hop=raw<1?Math.abs(Math.sin(raw*Math.PI*3))*24:0;
 const land=raw>=1?spring({frame:t-F_TRAVEL,fps:FPS,config:{damping:7,stiffness:140}}):0;
 const fadeOut=interpolate(t,[end-20,end],[1,0],{extrapolateLeft:"clamp",extrapolateRight:"clamp"});
 const tagIn=spring({frame:t-F_IN[1]+10,fps:FPS,config:{damping:13}}),left=!COLS[fz.to];
 const cols=["#17c394","#ff7eb6","#f2b560","#66b8ff","#a99bff"],ct=t-F_TRAVEL;
 return <>
  {/* doormat */}
  {raw>=1&&<div style={{position:"absolute",left:b.x-34,top:b.y-2,width:68,height:12,borderRadius:6,background:"#c98f5a",opacity:fadeOut*clamp(land*2,0,1),zIndex:4}}/>}
  {/* the item */}
  <div style={{position:"absolute",left:pos.x-30,top:pos.y-56-hop,width:60,height:60,display:"grid",placeItems:"center",fontSize:raw<1?40:44,zIndex:5,
   filter:"drop-shadow(0 6px 8px rgba(20,40,32,.3))",opacity:fadeOut,transform:`rotate(${raw<1?Math.sin(raw*12)*12:0}deg) scale(${raw<1?1:0.7+0.3*land})`}}>{fz.icon}</div>
  {/* confetti at landing */}
  {ct>=0&&ct<70&&Array.from({length:22},(_,i)=>{const ang=-Math.PI*(0.1+0.8*i/21),sp=4+(i%4)*1.4;
   return <div key={i} style={{position:"absolute",left:b.x+Math.cos(ang)*sp*ct,top:b.y-40+Math.sin(ang)*sp*ct+0.08*ct*ct,width:9,height:5,borderRadius:2,
    background:cols[i%5],transform:`rotate(${ct*15+i*40}deg)`,opacity:1-ct/70,zIndex:6}}/>})}
  {/* delivered tag */}
  {t>=F_IN[1]-10&&<div style={{position:"absolute",left:left?b.x+40:b.x-40-230,top:b.y-118,width:230,background:"#fff",borderRadius:16,padding:"10px 14px",
   boxShadow:"0 12px 28px rgba(20,40,32,.22)",borderLeft:"6px solid #17c394",opacity:tagIn*fadeOut,transform:`translateY(${(1-tagIn)*12}px)`,zIndex:6,fontFamily:"system-ui,Segoe UI,sans-serif"}}>
   <div style={{fontSize:12,fontWeight:800,letterSpacing:1.2,textTransform:"uppercase",color:"#0b8f69"}}>{fz.sale?"Sold ✓":"Delivered ✓"}</div>
   <div style={{fontSize:18,fontWeight:800,color:"#14201c",lineHeight:1.2,marginTop:2}}>{fz.label}</div>
   <div style={{fontSize:13,color:"#5b6b65",marginTop:3}}>{fz.note}</div></div>}
 </>}

function Scene(){
 useStore();const frame=useCurrentFrame(),s=store.s,sk=SKY[s.period]||SKY.day,night=s.period==="night";
 const live=s.packets.filter(p=>frame-p.f0>=0&&frame-p.f0<=D);
 const ids=Object.keys(COLS);
 const cam=zoomOf(frame);
 const th=s.think&&frame>=s.think.f0&&frame-s.think.f0<FPS*7?s.think:null,thSp=th?spring({frame:frame-th.f0,fps:FPS,config:{damping:14}})*interpolate(frame-th.f0,[FPS*6,FPS*7],[1,0],{extrapolateLeft:"clamp",extrapolateRight:"clamp"}):0;
 return <AbsoluteFill style={{background:`linear-gradient(${sk[0]},${sk[1]})`,overflow:"hidden",fontFamily:"system-ui,Segoe UI,sans-serif"}}>
  {night&&[[80,60],[220,140],[380,40],[1020,70],[1180,150],[1300,50],[150,300],[1250,330]].map(([x,y],i)=><div key={i} style={{position:"absolute",left:x,top:y,width:4,height:4,borderRadius:"50%",background:"#dfe6ff",opacity:0.3+0.7*Math.abs(Math.sin(frame/24+i))}}/>)}
  {store.backdrop&&<img src={store.backdrop} alt="" style={{position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"cover",
    transform:`scale(${1.04+Math.sin(frame/400)*0.01})`,filter:night?"brightness(.38) saturate(.7) hue-rotate(200deg)":s.period==="evening"?"saturate(1.1) sepia(.15)":s.period==="early morning"?"brightness(1.05) saturate(.9)":"none"}}/>}
  {!store.backdrop&&!night&&[[0,90,1],[500,40,0.8],[900,120,0.9]].map(([o,y,sc],i)=><div key={i} style={{position:"absolute",left:((frame*(0.3+i*0.1)+o)%1700)-250,top:y,width:150*sc,height:44*sc,borderRadius:44,background:"rgba(255,255,255,.8)"}}/>)}
  <div style={{position:"absolute",inset:0,transformOrigin:"0 0",transform:`translate(${cam.tx}px,${cam.ty}px) scale(${cam.z})`}}>
  {/* building */}
  <div style={{position:"absolute",left:B.x,top:B.y,width:B.w,height:B.h,background:night?"linear-gradient(180deg,#2b355c,#222a4a)":"linear-gradient(180deg,#f7fbfd,#e7f1f6)",border:"6px solid #1f6f9e",borderRadius:"34px 34px 0 0",boxShadow:"0 30px 70px rgba(20,40,60,.22)"}}/>
  <div style={{position:"absolute",left:B.x-60,top:B.y+B.h,width:B.w+120,height:8,background:"#1f6f9e",borderRadius:4}}/>
  {/* front door + steps + plants (from the sketch) */}
  <div style={{position:"absolute",left:SX-52,top:B.y+B.h-120,width:104,height:120,background:night?"#3a4570":"#d9ecf5",border:"5px solid #1f6f9e",borderBottom:"none",borderRadius:"14px 14px 0 0"}}><div style={{position:"absolute",right:14,top:58,width:10,height:10,borderRadius:"50%",background:"#1f6f9e"}}/></div>
  {[0,1].map(i=><div key={i} style={{position:"absolute",left:SX-80-i*20,top:B.y+B.h+8+i*14,width:160+i*40,height:14,background:"#cfdde5",border:"3px solid #1f6f9e",borderTop:i?"none":"3px solid #1f6f9e"}}/>)}
  {[-1,1].map(i=><div key={i} style={{position:"absolute",left:SX+i*82-14,top:B.y+B.h-46,fontSize:34}}>🪴</div>)}
  {/* wiring: dashed spine + branches, lit while a message travels */}
  <svg width={W} height={H} style={{position:"absolute",left:0,top:0}}>
   <line x1={SX} y1={ROOF.y} x2={SX} y2={B.y+B.h-122} stroke="#1f6f9e" strokeWidth={4} strokeDasharray="8 14" opacity={0.28}/>
   {ids.map(id=>{const d=DOOR(id);return <line key={id} x1={d.x} y1={d.y} x2={SX} y2={d.y} stroke="#1f6f9e" strokeWidth={4} strokeDasharray="8 14" opacity={0.28}/>})}
   {live.map(p=>{const id=p.from==="robot"?p.to:p.from,pts=PATH(id),t=ease(clamp((frame-p.f0)/D,0,1));
    const col=p.from==="robot"?"#17c394":(s.people[id]||{}).color||"#66b8ff";
    const d="M"+pts.map(q=>q.x+" "+q.y).join(" L");
    return <path key={p.id} d={d} stroke={col} strokeWidth={9} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={0.35+0.4*Math.sin(t*Math.PI)}/>})}
  </svg>
  {ids.map(id=><Apartment key={id} id={id} frame={frame}/>)}
  <Doors frame={frame}/>
  <Finale frame={frame}/>
  {/* travelling messages */}
  {live.map(p=>{const id=p.from==="robot"?p.to:p.from,pts=PATH(id),raw=clamp((frame-p.f0)/D,0,1),t=ease(raw);
   const pos=along(p.from==="robot"?pts.slice().reverse():pts,t),col=p.from==="robot"?"#17c394":(s.people[id]||{}).color||"#66b8ff";
   return <div key={p.id} style={{position:"absolute",left:pos.x-24,top:pos.y-24,width:48,height:48,borderRadius:"50%",background:col,border:"5px solid #fff",boxShadow:`0 0 0 ${6+Math.sin(frame/3)*3}px ${col}44,0 8px 18px rgba(20,40,32,.3)`,display:"grid",placeItems:"center",fontSize:22,transform:`scale(${0.8+0.4*Math.sin(raw*Math.PI)})`}}>{p.from==="robot"?"🤖":"💬"}</div>})}
  <Robot frame={frame}/>
  {/* request card (left of the robot) */}
  {s.req&&<div style={{position:"absolute",left:40,top:40,width:440,background:"#fff",borderRadius:20,padding:"16px 20px",boxShadow:"0 12px 30px rgba(20,40,32,.16)",borderLeft:"8px solid "+((s.people[s.asker]||{}).color||"#17c394")}}>
   <div style={{fontSize:14,fontWeight:800,letterSpacing:1.5,color:"#5b6b65",textTransform:"uppercase"}}>{s.req.kind==="sale"?"For sale by ":"Request from "}{(s.people[s.asker]||{}).name||""}</div>
   <div style={{fontSize:30,fontWeight:800,color:"#14201c",marginTop:2}}>{s.req.kind==="company"?"👥 ":s.req.kind==="favor"?"🤝 ":s.req.kind==="sale"?"🏷️ ":"📦 "}{s.req.item}</div>
   <div style={{display:"flex",gap:8,marginTop:8}}>{s.req.price&&<span style={{fontSize:15,background:"#17c394",color:"#fff",borderRadius:999,padding:"3px 12px",fontWeight:800}}>{s.req.price}</span>}{s.req.qty&&s.req.kind!=="sale"&&<span style={{fontSize:15,background:"#e4f8f0",color:"#0b8f69",borderRadius:999,padding:"3px 12px",fontWeight:700}}>{s.req.qty}</span>}
    {s.req.urgency&&<span style={{fontSize:15,background:s.req.urgency==="high"?"#ffe2dc":"#fff1c2",color:s.req.urgency==="high"?"#c23b25":"#8a6500",borderRadius:999,padding:"3px 12px",fontWeight:700}}>{s.req.urgency} urgency</span>}</div>
  </div>}
  {/* robot thought bubble (right of the robot) */}
  {th&&<div style={{position:"absolute",left:880,top:34,width:470,opacity:thSp,transform:`scale(${0.9+0.1*thSp})`,transformOrigin:"left center"}}>
   <div style={{background:night?"#e8f6f1":"#ffffff",borderRadius:24,padding:"14px 20px",boxShadow:"0 12px 30px rgba(20,40,32,.16)",border:"3px dashed #17c394"}}>
    <div style={{fontSize:14,fontWeight:800,letterSpacing:1.5,color:"#0b8f69",textTransform:"uppercase",marginBottom:3}}>🤖 thinking</div>
    <div style={{fontSize:20,lineHeight:1.3,color:"#14201c"}}>{th.text}</div></div>
   {[0,1].map(i=><div key={i} style={{position:"absolute",left:-22-i*20,top:70+i*16,width:16-i*5,height:16-i*5,borderRadius:"50%",background:"#fff",border:"3px dashed #17c394"}}/>)}
  </div>}
  {ids.map(id=><Bubble key={id} id={id} frame={frame}/>)}
  </div>
 </AbsoluteFill>}

let root=null;
function mount(el,people,onPick,backdrop){
 if(root){try{root.unmount()}catch(e){}root=null}
 store.s.people=people;store.onPick=onPick;store.backdrop=backdrop||null;store.ref=React.createRef();
 root=createRoot(el);
 root.render(<Player ref={store.ref} component={Scene} durationInFrames={FPS*3600} compositionWidth={W} compositionHeight={H} fps={FPS} loop autoPlay controls={false} clickToPlay={false} acknowledgeRemotionLicense style={{width:"100%",height:"100%"}}/>);
}
window.NMStreet={
 mount,D,FPS,
 say(from,to,text){const f=nowF(),t=String(text),txt=t.length>170?t.slice(0,167)+"…":t;
  store.s.packets=store.s.packets.filter(p=>f-p.f0<D+20);store.s.packets.push({id:Math.random(),from,to,f0:f});
  store.s.look=from==="robot"?to:from;
  if(from==="robot")store.s.bubbles[to]={from,text:txt,f0:f+D};else store.s.bubbles[from]={from,text:txt,f0:f};emit()},
 think(text){store.s.think={text:String(text),f0:nowF()};emit()},
 status(who,state){store.s.status[who]=state;emit()},
 typing(who,on){if(who==="robot")store.s.busy=!!on;else store.s.typing[who]=!!on;emit()},
 asker(id){store.s.asker=id;emit()},
 request(r){store.s.req=r;emit()},
 period(p){store.s.period=p;emit()},
 asleep(map){store.s.asleep=map||{};emit()},
 finale(o){store.s.finale={from:o.from,to:o.to,icon:o.icon||"📦",label:o.label||"",note:o.note||"",sale:!!o.sale,f0:nowF()};store.s.bubbles={};emit()},
 clear(){Object.assign(store.s,{req:null,think:null,packets:[],bubbles:{},status:{},typing:{},busy:false,look:null,finale:null});emit()},
};
