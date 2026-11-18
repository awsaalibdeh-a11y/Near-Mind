// NearMind Street: the coach's sketch, animated. Robot on the roof, ten apartments on five floors, every message travels the dashed spine.
// Driven live from the page through window.NMStreet (say / think / status / typing / asker / request / period / finale / clear).
import React,{useEffect,useState} from "react";
import {createRoot} from "react-dom/client";
import {Player} from "@remotion/player";
import {AbsoluteFill,useCurrentFrame,spring,Easing,interpolate} from "remotion";

const W=1400,H=1120,FPS=30,D=40;                      // D = frames a message takes to travel
const FLOORS=5,B={x:330,y:230,w:740,h:820};           // building
const AW=290,AH=124,SX=700,ROOF={x:700,y:B.y},EYE_Y=98;
const SKY={day:["#bfe3ff","#f1f9ff"],evening:["#ffc79a","#fdeee0"],"early morning":["#ffe0b5","#eef6ff"],night:["#16224d","#0a1022"]};
const PILL={asked:["asked","#fff1d6","#b0630f"],offer:["can help","#e2f1ff","#1f6fb8"],no:["can't","#eef1f0","#7c8a84"],
 chosen:["chosen ✓","#17c394","#fff"],released:["thanked","#eef6f2","#5f8f7b"]};
const FONT="system-ui,Segoe UI,sans-serif";

const store={s:{people:{},period:"day",busy:false,asker:null,req:null,think:null,packets:[],bubbles:{},status:{},statusF:{},why:{},typing:{},asleep:{},look:null,finale:null},subs:new Set(),ref:null,onPick:null};
const emit=()=>store.subs.forEach(f=>f());
const nowF=()=>{try{return store.ref.current.getCurrentFrame()}catch(e){return 0}};
function useStore(){const[,t]=useState(0);useEffect(()=>{const f=()=>t(x=>x+1);store.subs.add(f);return()=>store.subs.delete(f)},[])}
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const ease=Easing.inOut(Easing.cubic);

// layout comes from the apartment number: floor 1 is at the bottom, A on the left, B on the right
const apt=id=>String((store.s.people[id]||{}).apt||"1A");
const COL=id=>apt(id).slice(-1).toUpperCase()==="B"?1:0;
const ROW=id=>FLOORS-clamp(parseInt(apt(id),10)||1,1,FLOORS);
const AX=id=>COL(id)?750:360, AY=id=>B.y+42+ROW(id)*152;
const DOOR=id=>({x:COL(id)?750:650,y:AY(id)+AH/2});
const PATH=id=>{const d=DOOR(id);return [d,{x:SX,y:d.y},{x:SX,y:ROOF.y}]};
const FOOT=id=>({x:DOOR(id).x+(COL(id)?-24:24),y:AY(id)+AH-6});

function along(pts,t){            // point at fraction t along a polyline
 const seg=[];let L=0;for(let i=1;i<pts.length;i++){const l=Math.hypot(pts[i].x-pts[i-1].x,pts[i].y-pts[i-1].y);seg.push(l);L+=l}
 let d=t*L;for(let i=0;i<seg.length;i++){if(d<=seg[i]||i===seg.length-1){const f=seg[i]?d/seg[i]:0;return{x:pts[i].x+(pts[i+1].x-pts[i].x)*f,y:pts[i].y+(pts[i+1].y-pts[i].y)*f}}d-=seg[i]}
 return pts[pts.length-1]}

function Dots({frame,color="#8a9a93"}){return <div style={{display:"flex",gap:4}}>{[0,1,2].map(i=><div key={i} style={{width:7,height:7,borderRadius:"50%",background:color,transform:"translateY("+(-Math.abs(Math.sin(frame/5+i*0.9))*5)+"px)"}}/>)}</div>}

function Robot({frame}){
 const s=store.s,intro=spring({frame,fps:FPS,config:{damping:11,stiffness:90}}),bob=Math.sin(frame/22)*4;
 const last=s.packets.length?s.packets[s.packets.length-1]:null;
 const talking=last&&last.from==="robot"&&frame-last.f0>=0&&frame-last.f0<18;
 const heard=last&&last.to==="robot"&&frame-last.f0>=D&&frame-last.f0<D+14;
 const bounce=heard?Math.sin((frame-last.f0-D)/14*Math.PI)*-10:0;
 const look=s.look&&s.people[s.look]?{x:clamp((AX(s.look)+AW/2-SX)/90,-5,5),y:clamp((AY(s.look)-120)/180,-1,5)}:{x:Math.sin(frame/60)*2,y:0};
 const glow=s.busy?0.6+0.4*Math.sin(frame/4):0.25;
 const bl=frame%137,blink=bl<3?1-bl/3*0.9:bl<6?0.1+(bl-3)/3*0.9:1;       // blink every ~4.5s
 const eye=(cx)=><g><ellipse cx={cx} cy={EYE_Y} rx={21} ry={21*Math.max(blink,0.12)} fill="#fff" stroke="#1f6f9e" strokeWidth={4}/>
  {blink>0.5&&<circle cx={cx+look.x} cy={EYE_Y+look.y} r={9} fill="#14303f"/>}
  {s.busy&&blink>0.5&&<path d={`M${cx-7} ${EYE_Y} a7 7 0 1 1 7 7`} stroke="#35d6a4" strokeWidth={3} fill="none" transform={`rotate(${frame*12} ${cx} ${EYE_Y})`}/>}</g>;
 return <svg width={W} height={B.y+10} style={{position:"absolute",left:0,top:0,transform:`translateY(${(1-intro)*-180+bob+bounce}px)`,overflow:"visible"}}>
  <defs><radialGradient id="tip"><stop offset="0" stopColor="#7dffd5"/><stop offset="1" stopColor="#17c394" stopOpacity="0"/></radialGradient></defs>
  {s.busy&&[0,1,2].map(i=>{const r=((frame+i*14)%42)/42;return <circle key={i} cx={700} cy={98} r={70+r*90} fill="none" stroke="#17c394" strokeWidth={3} opacity={(1-r)*0.35}/>})}
  {[[640,40,612,12],[760,40,788,12]].map(([x1,y1,x2,y2],i)=><g key={i}><line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1f6f9e" strokeWidth={6} strokeLinecap="round"/>
   <circle cx={x2} cy={y2} r={16} fill="url(#tip)" opacity={glow}/><circle cx={x2} cy={y2} r={6} fill={s.busy?"#35d6a4":"#9fd8ee"}/></g>)}
  <rect x={590} y={38} width={220} height={120} rx={34} fill="#e9f6fb" stroke="#1f6f9e" strokeWidth={6}/>
  {eye(655)}{eye(745)}
  {talking?<ellipse cx={700} cy={135} rx={22} ry={8+Math.abs(Math.sin(frame/2))*6} fill="#1f6f9e"/>
   :<path d="M670 128 Q700 150 730 128" stroke="#1f6f9e" strokeWidth={6} fill="none" strokeLinecap="round"/>}
  <path d={`M560 ${B.y} L590 162 L810 162 L840 ${B.y} Z`} fill="#d4ecf6" stroke="#1f6f9e" strokeWidth={6} strokeLinejoin="round"/>
  <text x={700} y={B.y-24} textAnchor="middle" fontFamily={FONT} fontWeight={800} fontSize={20} letterSpacing={6} fill="#1f6f9e">NEARMIND</text>
 </svg>}

function Apartment({id,frame,i}){
 const s=store.s,p=s.people[id]||{name:id,apt:"",color:"#999",icon:"🏠"};
 const x=AX(id),y=AY(id),right=COL(id)===1,st=s.status[id],sale=s.req&&s.req.kind==="sale";
 const pill=sale&&st==="offer"?["wants it","#e2f1ff","#1f6fb8"]:sale&&st==="chosen"?["buyer ✓","#17c394","#fff"]:PILL[st];
 const sleep=s.asleep[id],asker=s.asker===id,typing=s.typing[id],night=s.period==="night";
 const hot=s.packets.some(k=>(k.from===id||k.to===id)&&frame-k.f0>=0&&frame-k.f0<=D+10);
 const border=asker?"#ff7eb6":{asked:"#f2b560",offer:"#66b8ff",chosen:"#17c394",no:"#c9d2ce",released:"#b6c9bf"}[st]||"#1f6f9e";
 const bg=sleep?"linear-gradient(180deg,#46527e,#2c365a)":night?"linear-gradient(180deg,#fff2c9,#ffe3a1)":"linear-gradient(180deg,#ffffff,#f1f7fb)";
 const pulse=asker?4+Math.sin(frame/6)*4:0;
 const intro=spring({frame:frame-8-i*3,fps:FPS,config:{damping:13,stiffness:120}});           // staggered entrance
 const pop=st&&s.statusF[id]!=null?spring({frame:frame-s.statusF[id],fps:FPS,config:{damping:8,stiffness:200}}):1;
 const dim=s.req&&!st&&!asker&&!hot?0.82:1;                                                   // neighbors not involved step back a little
 const tag=t=>({fontSize:13,fontWeight:800,letterSpacing:1,textTransform:"uppercase",borderRadius:999,padding:"3px 10px",whiteSpace:"nowrap"});
 return <div onClick={()=>store.onPick&&store.onPick(id)} style={{position:"absolute",left:x,top:y,width:AW,height:AH,cursor:"pointer",
   opacity:intro*dim,transform:`translateY(${(1-intro)*30}px) scale(${0.94+0.06*intro})`}}>
  <div style={{position:"absolute",inset:0,borderRadius:16,background:bg,border:"5px solid "+border,boxShadow:(asker?`0 0 0 ${pulse}px #ff7eb655,`:"")+(st==="chosen"?"0 0 0 8px #17c39433,":"")+"0 8px 22px rgba(20,40,32,.16)",
   padding:right?"12px 14px 12px 46px":"12px 46px 12px 14px",boxSizing:"border-box",color:sleep?"#e8ecff":"#14201c",fontFamily:FONT,display:"flex",alignItems:"center",gap:12,opacity:st==="released"?0.8:1}}>
   <div style={{width:68,height:68,borderRadius:"50%",background:p.color,overflow:"hidden",flex:"none",boxShadow:`0 0 0 4px #fff,0 0 0 ${hot?7:4}px ${hot?border:"#fff"}`,filter:sleep?"grayscale(.5) brightness(.75)":"none",display:"grid",placeItems:"center",fontWeight:800,fontSize:26,color:"#0b1a14"}}>
    {p.img?<img src={p.img} alt="" style={{width:"100%",height:"100%",objectFit:"cover"}}/>:p.name[0]}</div>
   <div style={{lineHeight:1.15,minWidth:0,flex:1}}>
    <div style={{display:"flex",alignItems:"baseline",gap:8,minWidth:0}}><span style={{fontWeight:800,fontSize:p.name.length>8?21:25,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",minWidth:0}}>{p.name}</span><span style={{fontSize:14,opacity:0.6,fontWeight:700,flex:"none"}}>{p.apt}</span>{p.members&&<span style={{fontSize:14,opacity:0.7,fontWeight:800,marginLeft:"auto",flex:"none",whiteSpace:"nowrap"}}>👪{p.members.length}</span>}</div>
    <div style={{display:"flex",alignItems:"center",gap:8,marginTop:7,minHeight:24}}>
     {asker&&<span style={{...tag(),background:"#ff7eb6",color:"#fff"}}>{sale?"selling":"asking"}</span>}
     {!asker&&pill&&<span style={{...tag(),background:pill[1],color:pill[2],display:"inline-block",transform:`scale(${0.6+0.4*pop})`}}>{pill[0]}</span>}
     {!asker&&!pill&&sleep&&<span style={{...tag(),background:"#e4e8fb",color:"#5b6aa8"}}>asleep</span>}
     {typing&&<div style={{background:sleep?"#ffffff22":"#eef3f1",borderRadius:999,padding:"7px 10px"}}><Dots frame={frame}/></div>}
    </div>
    {!asker&&s.why[id]&&<div style={{marginTop:6,fontSize:14,fontWeight:600,fontStyle:"italic",opacity:0.72,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",
      transform:`translateX(${(1-clamp((frame-s.why[id].f0)/12,0,1))*(right?12:-12)}px)`}}>💡 {s.why[id].text}</div>}
   </div>
   <div style={{position:"absolute",[right?"right":"left"]:-2,top:-2,transform:`translate(${right?14:-14}px,-14px) rotate(${hot?Math.sin(frame/3)*10:0}deg)`,fontSize:24,width:40,height:40,borderRadius:"50%",background:sleep?"#3a4570":"#fff",border:"3px solid "+border,display:"grid",placeItems:"center"}}>{p.icon}</div>
   {sleep&&[0,1,2].map(k=><div key={k} style={{position:"absolute",[right?"right":"left"]:16+k*14,bottom:40+((frame/2+k*14)%30)+k*4,fontWeight:800,fontSize:16+k*4,color:"#c9d3ff",opacity:0.9-k*0.25}}>z</div>)}
  </div>
 </div>}

// speech bubbles sit beside each apartment; a newer bubble on the same side pushes nearby older ones away so they never pile up
function Bubbles({frame}){
 const s=store.s,list=Object.entries(s.bubbles).filter(([id,b])=>frame>=b.f0&&s.people[id]);
 return <>{list.map(([id,b])=>{
  const age=frame-b.f0,side=COL(id);
  const newer=list.filter(([o,c])=>o!==id&&COL(o)===side&&c.f0>b.f0&&Math.abs(ROW(o)-ROW(id))<=1).map(([,c])=>c.f0);
  const kill=newer.length?Math.min(...newer)+6:null;
  const fade=Math.min(interpolate(age,[FPS*9,FPS*11],[1,0],{extrapolateLeft:"clamp",extrapolateRight:"clamp"}),kill==null?1:clamp(1-(frame-kill)/10,0,1));
  if(fade<=0)return null;
  const sp=spring({frame:age,fps:FPS,config:{damping:12,stiffness:160}}),p=s.people[id],left=!side,fromRobot=b.from==="robot";
  const x=left?22:1086,y=Math.min(AY(id)-8,H-210),w=292;
  return <div key={id} style={{position:"absolute",left:x,top:y,width:w,zIndex:8,opacity:sp*fade,transform:`translateX(${(1-sp)*(left?30:-30)}px) scale(${0.85+0.15*sp})`,transformOrigin:left?"right center":"left center",fontFamily:FONT}}>
   <div style={{background:"#fff",borderRadius:18,padding:"10px 14px",boxShadow:"0 10px 28px rgba(20,40,32,.18)",borderTop:"6px solid "+(fromRobot?"#17c394":p.color),position:"relative"}}>
    <div style={{fontSize:12,fontWeight:800,letterSpacing:1,textTransform:"uppercase",color:fromRobot?"#0b8f69":"#36424a",marginBottom:3}}>{fromRobot?"🤖 NearMind → "+p.name:p.name+" → 🤖 NearMind"}</div>
    <div style={{fontSize:18,lineHeight:1.3,color:"#14201c"}}>{b.text}</div>
    <div style={{position:"absolute",top:30,[left?"right":"left"]:-12,width:0,height:0,borderTop:"12px solid transparent",borderBottom:"12px solid transparent",[left?"borderLeft":"borderRight"]:"14px solid #fff"}}/>
   </div></div>})}</>}

// ---------- finale: the item travels door to door, camera zooms on the receiver's door, item lands on the doormat ----------
const F_TRAVEL=70,F_IN=[55,95],F_HOLD=165,F_OUT=36;
function zoomOf(frame){
 const fz=store.s.finale;if(!fz||frame<fz.f0)return{z:1,tx:0,ty:0,k:0};
 const t=frame-fz.f0,end=F_IN[1]+F_HOLD;
 let k=t<F_IN[0]?0:t<F_IN[1]?(t-F_IN[0])/(F_IN[1]-F_IN[0]):t<end?1:t<end+F_OUT?1-(t-end)/F_OUT:0;
 k=ease(clamp(k,0,1));
 const f=FOOT(fz.to),fx=f.x+(COL(fz.to)?-60:60),fy=f.y-50,z=1+1.35*k;   // focus point eases to screen centre as we zoom
 return{z,tx:k*(W/2-fx*z),ty:k*(H/2-fy*z),k};
}
function Doors({frame,ids}){
 const fz=store.s.finale,t=fz?frame-fz.f0:-1,night=store.s.period==="night";
 return <>{ids.map(id=>{const d=DOOR(id),r=COL(id),on=fz&&fz.to===id&&t>=F_IN[0]&&t<F_IN[1]+F_HOLD+F_OUT;
  const open=on?Math.sin(clamp((t-F_IN[1])/20,0,1)*Math.PI/2)*55:0;                         // the door swings open as the item lands
  return <div key={id} style={{position:"absolute",left:d.x-(r?0:30)+(r?5:-5),top:AY(id)+AH-58,width:30,height:52,zIndex:3,perspective:200}}>
   <div style={{position:"absolute",inset:0,borderRadius:"7px 7px 0 0",background:on?"#ffe9a8":"#123"}}/>
   <div style={{position:"absolute",inset:0,borderRadius:"7px 7px 0 0",background:night?"#3a4570":"#d9ecf5",border:"4px solid "+(on?"#17c394":"#1f6f9e"),borderBottom:"none",
    transformOrigin:r?"left center":"right center",transform:`rotateY(${(r?-1:1)*open}deg)`,boxShadow:on?`0 0 0 ${6+Math.sin(frame/4)*3}px #17c39444`:"none"}}>
    <div style={{position:"absolute",[r?"right":"left"]:4,top:22,width:6,height:6,borderRadius:"50%",background:"#1f6f9e"}}/></div></div>})}</>}
function Finale({frame}){
 const fz=store.s.finale;if(!fz||frame<fz.f0)return null;
 const t=frame-fz.f0,end=F_IN[1]+F_HOLD+F_OUT;if(t>end+10)return null;
 const a=FOOT(fz.from),b=FOOT(fz.to),pts=[a,{x:SX,y:a.y},{x:SX,y:b.y},b];
 const raw=clamp(t/F_TRAVEL,0,1),pos=raw<1?along(pts,Easing.inOut(Easing.quad)(raw)):b;
 const hop=raw<1?Math.abs(Math.sin(raw*Math.PI*3))*24:0;
 const land=raw>=1?spring({frame:t-F_TRAVEL,fps:FPS,config:{damping:7,stiffness:140}}):0;
 const fadeOut=interpolate(t,[end-20,end],[1,0],{extrapolateLeft:"clamp",extrapolateRight:"clamp"});
 const tagIn=spring({frame:t-F_IN[1]+10,fps:FPS,config:{damping:13}}),left=!COL(fz.to);
 const cols=["#17c394","#ff7eb6","#f2b560","#66b8ff","#a99bff"],ct=t-F_TRAVEL;
 return <>
  {raw<1&&[1,2,3].map(k=>{const q=along(pts,Easing.inOut(Easing.quad)(clamp(raw-k*0.035,0,1)));
   return <div key={k} style={{position:"absolute",left:q.x-10+k,top:q.y-36,width:20-k*4,height:20-k*4,borderRadius:"50%",background:"#ffd36b",opacity:0.5-k*0.13,zIndex:5}}/>})}
  {raw>=1&&<div style={{position:"absolute",left:b.x-34,top:b.y-4,width:68,height:10,borderRadius:6,background:"#c98f5a",opacity:fadeOut*clamp(land*2,0,1),zIndex:4}}/>}
  {raw>=1&&<div style={{position:"absolute",left:b.x-26,top:b.y-2,width:52,height:8,borderRadius:"50%",background:"rgba(0,0,0,.18)",transform:`scaleX(${0.6+0.4*land})`,opacity:fadeOut,zIndex:4}}/>}
  <div style={{position:"absolute",left:pos.x-30,top:pos.y-58-hop,width:60,height:60,display:"grid",placeItems:"center",fontSize:raw<1?40:44,zIndex:5,
   filter:"drop-shadow(0 6px 8px rgba(20,40,32,.3))",opacity:fadeOut,transform:`rotate(${raw<1?Math.sin(raw*12)*12:0}deg) scale(${raw<1?1:0.7+0.3*land},${raw<1?1:0.7+0.3*land+(1-land)*0.15})`}}>{fz.icon}</div>
  {ct>=0&&ct<70&&Array.from({length:26},(_,i)=>{const ang=-Math.PI*(0.08+0.84*i/25),sp=4+(i%4)*1.4;
   return <div key={i} style={{position:"absolute",left:b.x+Math.cos(ang)*sp*ct,top:b.y-40+Math.sin(ang)*sp*ct+0.08*ct*ct,width:9,height:5,borderRadius:2,
    background:cols[i%5],transform:`rotate(${ct*15+i*40}deg)`,opacity:1-ct/70,zIndex:6}}/>})}
  {t>=F_IN[1]-10&&<div style={{position:"absolute",left:left?b.x+40:b.x-40-230,top:b.y-118,width:230,background:"#fff",borderRadius:16,padding:"10px 14px",
   boxShadow:"0 12px 28px rgba(20,40,32,.22)",borderLeft:"6px solid #17c394",opacity:tagIn*fadeOut,transform:`translateY(${(1-tagIn)*12}px)`,zIndex:9,fontFamily:FONT}}>
   <div style={{fontSize:12,fontWeight:800,letterSpacing:1.2,textTransform:"uppercase",color:"#0b8f69"}}>{fz.sale?"Sold ✓":"Delivered ✓"}</div>
   <div style={{fontSize:18,fontWeight:800,color:"#14201c",lineHeight:1.2,marginTop:2}}>{fz.label}</div>
   <div style={{fontSize:13,color:"#5b6b65",marginTop:3}}>{fz.note}</div></div>}
 </>}

// ---------- the robot scanning the building when it decides who to ask ----------
function Scan({frame,ids}){
 const th=store.s.think;if(!th||frame<th.f0||frame-th.f0>50)return null;
 const t=frame-th.f0,sorted=ids.slice().sort((a,b)=>ROW(a)-ROW(b)||COL(a)-COL(b));
 return <svg width={W} height={H} style={{position:"absolute",left:0,top:0,pointerEvents:"none",zIndex:2}}>
  {sorted.map((id,i)=>{const d=DOOR(id),k=t-i*2.5;if(k<0||k>22)return null;const o=Math.sin(k/22*Math.PI)*(store.s.asleep[id]?0.25:0.6);
   return <g key={id} opacity={o}><line x1={SX} y1={160} x2={COL(id)?AX(id)+AW/2:AX(id)+AW/2} y2={AY(id)+8} stroke="#17c394" strokeWidth={3} strokeDasharray="4 8"/>
    <circle cx={AX(id)+AW/2} cy={AY(id)+8} r={8+k*0.6} fill="none" stroke="#17c394" strokeWidth={3}/></g>})}
 </svg>}

// ---------- quiet counter: how few neighbors were bothered ----------
function Reach({frame,ids}){
 const s=store.s;if(!s.req)return null;
 const asked=Object.keys(s.status).filter(id=>s.status[id]).length,spared=Math.max(0,ids.length-1-asked);
 const sp=spring({frame:frame-(s.req.f0||0),fps:FPS,config:{damping:14}});
 return <div style={{position:"absolute",left:40,top:H-150,width:250,background:"#fff",borderRadius:18,padding:"12px 16px",boxShadow:"0 10px 26px rgba(20,40,32,.14)",
   opacity:sp,transform:`translateY(${(1-sp)*16}px)`,fontFamily:FONT,zIndex:7}}>
  <div style={{fontSize:12,fontWeight:800,letterSpacing:1.2,textTransform:"uppercase",color:"#5b6b65"}}>Neighbors contacted</div>
  <div style={{display:"flex",alignItems:"baseline",gap:6,marginTop:2}}><span style={{fontSize:34,fontWeight:800,color:"#14201c"}}>{asked}</span><span style={{fontSize:18,color:"#5b6b65",fontWeight:700}}>of {ids.length-1}</span></div>
  <div style={{display:"flex",gap:3,marginTop:6}}>{ids.filter(id=>id!==s.asker).map(id=><div key={id} style={{flex:1,height:6,borderRadius:3,background:s.status[id]?"#17c394":"#e3ece8"}}/>)}</div>
  <div style={{fontSize:13,color:"#0b8f69",fontWeight:700,marginTop:6}}>{spared} left in peace 🤫</div>
 </div>}

function Scene(){
 useStore();const frame=useCurrentFrame(),s=store.s,sk=SKY[s.period]||SKY.day,night=s.period==="night";
 const live=s.packets.filter(p=>frame-p.f0>=0&&frame-p.f0<=D+18);
 const ids=Object.keys(s.people);
 const cam=zoomOf(frame);
 const th=s.think&&frame>=s.think.f0&&frame-s.think.f0<FPS*7?s.think:null,thSp=th?spring({frame:frame-th.f0,fps:FPS,config:{damping:14}})*interpolate(frame-th.f0,[FPS*6,FPS*7],[1,0],{extrapolateLeft:"clamp",extrapolateRight:"clamp"}):0;
 const bIn=spring({frame,fps:FPS,config:{damping:16,stiffness:70}});
 return <AbsoluteFill style={{background:`linear-gradient(${sk[0]},${sk[1]})`,overflow:"hidden",fontFamily:FONT}}>
  {night&&[[80,60],[220,140],[380,40],[1020,70],[1180,150],[1300,50],[150,300],[1250,330]].map(([x,y],i)=><div key={i} style={{position:"absolute",left:x,top:y,width:4,height:4,borderRadius:"50%",background:"#dfe6ff",opacity:0.3+0.7*Math.abs(Math.sin(frame/24+i))}}/>)}
  {store.backdrop&&<img src={store.backdrop} alt="" style={{position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"cover",
    transform:`scale(${1.04+Math.sin(frame/400)*0.01})`,filter:night?"brightness(.38) saturate(.7) hue-rotate(200deg)":s.period==="evening"?"saturate(1.1) sepia(.15)":s.period==="early morning"?"brightness(1.05) saturate(.9)":"none"}}/>}
  {!store.backdrop&&!night&&[[0,90,1],[500,40,0.8],[900,120,0.9]].map(([o,y,sc],i)=><div key={i} style={{position:"absolute",left:((frame*(0.3+i*0.1)+o)%1700)-250,top:y,width:150*sc,height:44*sc,borderRadius:44,background:"rgba(255,255,255,.8)"}}/>)}
  <div style={{position:"absolute",inset:0,transformOrigin:"0 0",transform:`translate(${cam.tx}px,${cam.ty}px) scale(${cam.z})`}}>
  {/* building rises in */}
  <div style={{position:"absolute",left:B.x,top:B.y,width:B.w,height:B.h,background:night?"linear-gradient(180deg,#2b355c,#222a4a)":"linear-gradient(180deg,#f7fbfd,#e7f1f6)",border:"6px solid #1f6f9e",borderRadius:"34px 34px 0 0",boxShadow:"0 30px 70px rgba(20,40,60,.22)",
   transformOrigin:"50% 100%",transform:`scaleY(${0.6+0.4*bIn})`,opacity:bIn}}/>
  {Array.from({length:FLOORS-1},(_,i)=><div key={i} style={{position:"absolute",left:B.x+18,top:B.y+42+(i+1)*152-14,width:B.w-36,height:2,background:night?"#3a4570":"#d5e5ee",opacity:bIn}}/>)}
  {Array.from({length:FLOORS},(_,i)=><div key={i} style={{position:"absolute",left:SX-15,top:B.y+42+i*152+AH/2+14,width:30,textAlign:"center",fontSize:12,fontWeight:800,color:night?"#8a97c8":"#8fb3c6",opacity:bIn}}>{FLOORS-i}</div>)}
  <div style={{position:"absolute",left:B.x-60,top:B.y+B.h,width:B.w+120,height:8,background:"#1f6f9e",borderRadius:4}}/>
  {/* front door + steps + plants (from the sketch) */}
  <div style={{position:"absolute",left:SX-46,top:B.y+B.h-92,width:92,height:92,background:night?"#3a4570":"#d9ecf5",border:"5px solid #1f6f9e",borderBottom:"none",borderRadius:"14px 14px 0 0"}}><div style={{position:"absolute",right:12,top:44,width:10,height:10,borderRadius:"50%",background:"#1f6f9e"}}/></div>
  {[0,1].map(i=><div key={i} style={{position:"absolute",left:SX-80-i*20,top:B.y+B.h+8+i*14,width:160+i*40,height:14,background:"#cfdde5",border:"3px solid #1f6f9e",borderTop:i?"none":"3px solid #1f6f9e"}}/>)}
  {[-1,1].map(i=><div key={i} style={{position:"absolute",left:SX+i*78-16,top:B.y+B.h-42,fontSize:32}}>🪴</div>)}
  {/* wiring: dashed spine + branches, lit while a message travels */}
  <svg width={W} height={H} style={{position:"absolute",left:0,top:0}}>
   <line x1={SX} y1={ROOF.y} x2={SX} y2={B.y+B.h-94} stroke="#1f6f9e" strokeWidth={4} strokeDasharray="8 14" strokeDashoffset={-frame*0.6} opacity={0.28}/>
   {ids.map(id=>{const d=DOOR(id);return <line key={id} x1={d.x} y1={d.y} x2={SX} y2={d.y} stroke="#1f6f9e" strokeWidth={4} strokeDasharray="8 14" opacity={0.28}/>})}
   {live.map(p=>{const id=p.from==="robot"?p.to:p.from;if(!s.people[id])return null;const pts=PATH(id),t=ease(clamp((frame-p.f0)/D,0,1));
    const col=p.from==="robot"?"#17c394":(s.people[id]||{}).color||"#66b8ff";
    const d="M"+pts.map(q=>q.x+" "+q.y).join(" L");
    return <path key={p.id} d={d} stroke={col} strokeWidth={9} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={(0.35+0.4*Math.sin(t*Math.PI))*interpolate(frame-p.f0,[D,D+18],[1,0],{extrapolateLeft:"clamp",extrapolateRight:"clamp"})}/>})}
  </svg>
  <Scan frame={frame} ids={ids}/>
  {ids.map((id,i)=><Apartment key={id} id={id} i={i} frame={frame}/>)}
  <Doors frame={frame} ids={ids}/>
  <Finale frame={frame}/>
  {/* travelling messages: a glowing dot with a short trail, and a ripple where it lands */}
  {live.map(p=>{const id=p.from==="robot"?p.to:p.from;if(!s.people[id])return null;const pts=PATH(id),dir=p.from==="robot"?pts.slice().reverse():pts,age=frame-p.f0,raw=clamp(age/D,0,1),t=ease(raw);
   const col=p.from==="robot"?"#17c394":(s.people[id]||{}).color||"#66b8ff";
   if(age>D){const end=dir[dir.length-1],r=(age-D)/18;return <div key={p.id} style={{position:"absolute",left:end.x-20-r*30,top:end.y-20-r*30,width:40+r*60,height:40+r*60,borderRadius:"50%",border:`4px solid ${col}`,opacity:1-r,zIndex:4}}/>}
   const pos=along(dir,t);
   return <React.Fragment key={p.id}>
    {[1,2,3,4].map(k=>{const q=along(dir,ease(clamp(raw-k*0.045,0,1)));return <div key={k} style={{position:"absolute",left:q.x-(14-k*2),top:q.y-(14-k*2),width:28-k*4,height:28-k*4,borderRadius:"50%",background:col,opacity:0.45-k*0.09,zIndex:4}}/>})}
    <div style={{position:"absolute",left:pos.x-24,top:pos.y-24,width:48,height:48,borderRadius:"50%",background:col,border:"5px solid #fff",boxShadow:`0 0 0 ${6+Math.sin(frame/3)*3}px ${col}44,0 8px 18px rgba(20,40,32,.3)`,display:"grid",placeItems:"center",fontSize:22,zIndex:5,transform:`scale(${0.8+0.4*Math.sin(raw*Math.PI)})`}}>{p.from==="robot"?"🤖":"💬"}</div>
   </React.Fragment>})}
  <Robot frame={frame}/>
  {/* request card (left of the robot) */}
  {s.req&&(()=>{const sp=spring({frame:frame-(s.req.f0||0),fps:FPS,config:{damping:13}});return <div style={{position:"absolute",left:40,top:36,width:440,background:"#fff",borderRadius:20,padding:"16px 20px",boxShadow:"0 12px 30px rgba(20,40,32,.16)",borderLeft:"8px solid "+((s.people[s.asker]||{}).color||"#17c394"),
   opacity:sp,transform:`translateX(${(1-sp)*-40}px)`,zIndex:7}}>
   <div style={{fontSize:14,fontWeight:800,letterSpacing:1.5,color:"#5b6b65",textTransform:"uppercase"}}>{s.req.kind==="sale"?"For sale by ":"Request from "}{(s.people[s.asker]||{}).name||""}</div>
   <div style={{fontSize:30,fontWeight:800,color:"#14201c",marginTop:2}}>{s.req.kind==="company"?"👥 ":s.req.kind==="favor"?"🤝 ":s.req.kind==="sale"?"🏷️ ":"📦 "}{s.req.item}</div>
   <div style={{display:"flex",gap:8,marginTop:8}}>{s.req.price&&<span style={{fontSize:15,background:"#17c394",color:"#fff",borderRadius:999,padding:"3px 12px",fontWeight:800}}>{s.req.price}</span>}{s.req.qty&&s.req.kind!=="sale"&&<span style={{fontSize:15,background:"#e4f8f0",color:"#0b8f69",borderRadius:999,padding:"3px 12px",fontWeight:700}}>{s.req.qty}</span>}
    {s.req.urgency&&<span style={{fontSize:15,background:s.req.urgency==="high"?"#ffe2dc":"#fff1c2",color:s.req.urgency==="high"?"#c23b25":"#8a6500",borderRadius:999,padding:"3px 12px",fontWeight:700}}>{s.req.urgency} urgency</span>}</div>
  </div>})()}
  {/* robot thought bubble (right of the robot) */}
  {th&&<div style={{position:"absolute",left:880,top:30,width:470,opacity:thSp,transform:`scale(${0.9+0.1*thSp})`,transformOrigin:"left center",zIndex:7}}>
   <div style={{background:night?"#e8f6f1":"#ffffff",borderRadius:24,padding:"14px 20px",boxShadow:"0 12px 30px rgba(20,40,32,.16)",border:"3px dashed #17c394"}}>
    <div style={{fontSize:14,fontWeight:800,letterSpacing:1.5,color:"#0b8f69",textTransform:"uppercase",marginBottom:3}}>🤖 thinking</div>
    <div style={{fontSize:20,lineHeight:1.3,color:"#14201c"}}>{th.text}</div></div>
   {[0,1].map(i=><div key={i} style={{position:"absolute",left:-22-i*20,top:70+i*16,width:16-i*5,height:16-i*5,borderRadius:"50%",background:"#fff",border:"3px dashed #17c394"}}/>)}
  </div>}
  <Reach frame={frame} ids={ids}/>
  <Bubbles frame={frame}/>
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
 mount,D,FPS,W,H,
 say(from,to,text){const f=nowF(),t=String(text),txt=t.length>150?t.slice(0,147)+"…":t;
  store.s.packets=store.s.packets.filter(p=>f-p.f0<D+20);store.s.packets.push({id:Math.random(),from,to,f0:f});
  store.s.look=from==="robot"?to:from;
  if(from==="robot")store.s.bubbles[to]={from,text:txt,f0:f+D};else store.s.bubbles[from]={from,text:txt,f0:f};emit()},
 think(text){store.s.think={text:String(text),f0:nowF()};emit()},
 why(who,text){store.s.why[who]={text:String(text),f0:nowF()};emit()},
 status(who,state){if(store.s.status[who]!==state)store.s.statusF[who]=nowF();store.s.status[who]=state;emit()},
 typing(who,on){if(who==="robot")store.s.busy=!!on;else store.s.typing[who]=!!on;emit()},
 asker(id){store.s.asker=id;emit()},
 request(r){store.s.req=Object.assign({f0:store.s.req?store.s.req.f0:nowF()},r);emit()},
 period(p){store.s.period=p;emit()},
 asleep(map){store.s.asleep=map||{};emit()},
 finale(o){store.s.finale={from:o.from,to:o.to,icon:o.icon||"📦",label:o.label||"",note:o.note||"",sale:!!o.sale,f0:nowF()};store.s.bubbles={};emit()},
 clear(){Object.assign(store.s,{req:null,think:null,packets:[],bubbles:{},status:{},statusF:{},why:{},typing:{},busy:false,look:null,finale:null});emit()},
};
