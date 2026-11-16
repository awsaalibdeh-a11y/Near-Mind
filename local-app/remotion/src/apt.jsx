import React,{useEffect,useState} from "react";
import {createRoot} from "react-dom/client";
import {Player} from "@remotion/player";
import {AbsoluteFill,useCurrentFrame,useVideoConfig,spring,Easing} from "remotion";

const W=1000,H=640;
const FX={x0:90,y0:132,w:820,h:440,pad:26,gap:24};
const UW=(FX.w-FX.pad*2-FX.gap)/2,UH=(FX.h-FX.pad*2-FX.gap)/2;
const POS=k=>({x:FX.x0+FX.pad+((k-1)%2)*(UW+FX.gap),y:FX.y0+FX.pad+Math.floor((k-1)/2)*(UH+FX.gap)});
const CEN=k=>{const p=POS(k);return{x:p.x+UW/2,y:p.y+UH/2}};
const HUB={x:FX.x0+FX.w/2,y:FX.y0+FX.h/2};
const SKY={day:["#bfe3ff","#eef8ff"],evening:["#ffcfa3","#fdeedd"],"early morning":["#ffe2b8","#eef6ff"],night:["#1a2756","#0b1124"]};

const store={s:{period:"day",busy:false,people:[],units:{},packets:[],parcel:null},subs:new Set(),ref:null};
const emit=()=>store.subs.forEach(f=>f());
const nowF=()=>{try{return store.ref.current.getCurrentFrame()}catch(e){return 0}};
const U=k=>store.s.units[k]||(store.s.units[k]={});
function useStore(){const[,t]=useState(0);useEffect(()=>{const f=()=>t(x=>x+1);store.subs.add(f);return()=>store.subs.delete(f)},[])}
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));

function Dots({frame}){return <div style={{display:"flex",gap:6,background:"#fff",borderRadius:999,padding:"9px 14px",boxShadow:"0 3px 10px rgba(20,40,32,.15)",alignSelf:"flex-start"}}>
 {[0,1,2].map(i=><div key={i} style={{width:9,height:9,borderRadius:"50%",background:"#8a9a93",transform:"translateY("+(-Math.abs(Math.sin(frame/5+i*0.9))*7)+"px)"}}/>)}</div>}

const PILL={asked:["asked","#fff1d6","#b0630f"],offer:["has it","#e2f1ff","#1f6fb8"],won:["chosen","#17c394","#fff"],done:["released","#eef2f0","#7c8a84"],skip:["let sleep","#e4e8fb","#5b6aa8"]};

function Unit({k,frame,fps}){
 const u=U(k),p=POS(k),person=store.s.people[k-1]||{n:"?",c:"#999",apt:""};
 const sleep=u.sleep,lit=u.lit&&!sleep,st=u.status||"idle";
 const bg=sleep?"linear-gradient(180deg,#45517c,#2b3558)":lit?"linear-gradient(180deg,#fff2c9,#ffe19a)":"linear-gradient(180deg,#e3edf6,#d2dee9)";
 const border={asked:"#f2b560",offer:"#66b8ff",won:"#17c394",done:"#b6c2bc"}[st]||"#ffffff";
 const bob=Math.sin(frame/18+k)*2.5;
 const say=u.say,sp=say?spring({frame:frame-say.f0,fps,config:{damping:13,stiffness:150}}):0;
 const pill=PILL[st];
 return <div style={{position:"absolute",left:p.x,top:p.y,width:UW,height:UH,borderRadius:18,background:bg,border:"5px solid "+border,boxShadow:st==="won"?"0 0 0 8px #17c39433,0 6px 22px #17c39455":lit?"0 6px 26px #ffd36b88":"0 5px 16px rgba(20,40,32,.16)",color:sleep?"#e8ecff":"#14201c",padding:"14px 18px",boxSizing:"border-box",display:"flex",flexDirection:"column",gap:10,opacity:st==="done"?0.82:1,overflow:"hidden",fontFamily:"system-ui,Segoe UI,sans-serif"}}>
  <div style={{display:"flex",alignItems:"center",gap:12}}>
   <div style={{width:46,height:46,borderRadius:"50%",background:person.c,display:"grid",placeItems:"center",fontWeight:800,fontSize:22,color:"#06130f",boxShadow:"0 0 0 3px #fff",transform:"translateY("+bob+"px)"}}>{person.n[0]}</div>
   <div style={{lineHeight:1.15}}><div style={{fontWeight:800,fontSize:23}}>{person.n}{k===1?" (you)":""}</div><div style={{fontSize:16,opacity:0.7}}>Apartment {person.apt}</div></div>
   {k>1&&(pill||sleep)&&<div style={{marginLeft:"auto",fontSize:15,fontWeight:800,textTransform:"uppercase",letterSpacing:1,background:pill?pill[1]:"#e4e8fb",color:pill?pill[2]:"#5b6aa8",borderRadius:999,padding:"4px 14px"}}>{pill?pill[0]:"asleep"}</div>}
  </div>
  {k>1&&u.real&&<div style={{alignSelf:"flex-start",fontSize:15,fontWeight:800,background:u.real.bg,color:u.real.fg,border:"2px solid "+u.real.bd,borderRadius:999,padding:"3px 13px",boxShadow:u.real.pulse?"0 0 0 "+(4+Math.sin(frame/6)*3)+"px "+u.real.bd+"55":"none"}}>{u.real.t}</div>}
  <div style={{flex:1,display:"flex",flexDirection:"column",justifyContent:"flex-end",gap:8,minHeight:0}}>
   {u.typing&&<Dots frame={frame}/>}
   {say&&<div style={{background:"#fff",color:"#14201c",borderRadius:"16px 16px 16px 4px",padding:"9px 14px",fontSize:19,lineHeight:1.3,boxShadow:"0 3px 12px rgba(20,40,32,.16)",borderLeft:say.who==="ai"?"5px solid #17c394":"5px solid #66b8ff",opacity:sp,transform:"translateY("+((1-sp)*14)+"px) scale("+(0.9+0.1*sp)+")",transformOrigin:"bottom left",maxHeight:UH-118,overflow:"hidden"}}>
     <div style={{fontSize:13,fontWeight:800,letterSpacing:1,textTransform:"uppercase",color:say.who==="ai"?"#0b8f69":"#2f8fe6",marginBottom:2}}>{say.who==="ai"?"NearMind":person.n}</div>{say.text}</div>}
  </div>
  {sleep&&[0,1,2].map(i=><div key={i} style={{position:"absolute",right:26+i*16,top:70-((frame/2+i*14)%38)-i*6,fontWeight:800,fontSize:20+i*5,color:"#c9d3ff",opacity:0.9-i*0.2}}>z</div>)}
 </div>}

function Scene(){
 useStore();const frame=useCurrentFrame(),{fps}=useVideoConfig(),s=store.s;
 const sk=SKY[s.period]||SKY.day,night=s.period==="night";
 const stars=[[60,50],[180,90],[300,36],[470,70],[640,30],[760,84],[930,44],[120,160],[860,150],[560,110]];
 const live=s.packets.filter(p=>frame-p.f0>=0&&frame-p.f0<=26);
 const hot={};live.forEach(p=>{hot[p.ph]=1});
 const pulse=s.busy?1+Math.sin(frame/4)*0.06:1;
 return <AbsoluteFill style={{background:"linear-gradient("+sk[0]+","+sk[1]+")",fontFamily:"system-ui,Segoe UI,sans-serif",overflow:"hidden"}}>
  {night&&stars.map(([x,y],i)=><div key={i} style={{position:"absolute",left:x,top:y,width:4,height:4,borderRadius:"50%",background:"#dfe6ff",opacity:0.35+0.65*Math.abs(Math.sin(frame/22+i))}}/>)}
  <div style={{position:"absolute",left:850+Math.sin(frame/60)*4,top:36,width:64,height:64,borderRadius:"50%",background:night?"#e4e9ff":"#ffc94d",boxShadow:night?"0 0 30px #aab6ff88":"0 0 60px #ffc94d99"}}>{night&&<div style={{position:"absolute",left:16,top:-6,width:60,height:60,borderRadius:"50%",background:sk[0]}}/>}</div>
  {!night&&[[0,60,1],[420,110,0.8],[700,30,0.9]].map(([o,y,sc],i)=><div key={i} style={{position:"absolute",left:((frame*(0.35+i*0.12)+o)%1300)-200,top:y,width:150*sc,height:44*sc,borderRadius:44,background:"rgba(255,255,255,.85)",boxShadow:(40*sc)+"px 12px 0 -6px rgba(255,255,255,.85),"+(-34*sc)+"px 14px 0 -8px rgba(255,255,255,.85)"}}/>)}
  <div style={{position:"absolute",left:FX.x0+40,top:FX.y0-52,width:FX.w-80,height:54,background:"linear-gradient(180deg,#9fb0a9,#bccac4)",clipPath:"polygon(6% 100%,14% 0,86% 0,94% 100%)",display:"grid",placeItems:"center",color:"#fff",fontWeight:800,letterSpacing:6,fontSize:20}}>NEARMIND</div>
  <div style={{position:"absolute",left:FX.x0,top:FX.y0,width:FX.w,height:FX.h,background:"linear-gradient(180deg,#f4eadf,#eadfd2)",border:"3px solid #d8cbbb",borderRadius:"8px 8px 0 0",boxShadow:"0 24px 60px rgba(20,40,32,.2)"}}/>
  <div style={{position:"absolute",left:FX.x0-14,top:FX.y0+FX.h,width:FX.w+28,height:26,background:"#b8c4be",borderRadius:"0 0 10px 10px"}}/>
  <svg width={W} height={H} style={{position:"absolute",left:0,top:0}}>
   {[1,2,3,4].map(k=>{const c=CEN(k);return <line key={k} x1={HUB.x} y1={HUB.y} x2={c.x} y2={c.y} stroke="#17c394" strokeWidth={hot[k]?7:4} strokeLinecap="round" strokeDasharray={hot[k]?"0":"3 16"} strokeDashoffset={-frame*0.8} opacity={hot[k]?1:0.45}/>})}
  </svg>
  {[1,2,3,4].map(k=><Unit key={k} k={k} frame={frame} fps={fps}/>)}
  {s.busy&&[0,1].map(i=>{const t=((frame/32)+i*0.5)%1;return <div key={i} style={{position:"absolute",left:HUB.x-42,top:HUB.y-42,width:84,height:84,borderRadius:"50%",border:"4px solid #17c394",opacity:(1-t)*0.8,transform:"scale("+(1+t*1.5)+")"}}/>})}
  <div style={{position:"absolute",left:HUB.x-44,top:HUB.y-44,width:88,height:88,borderRadius:"50%",background:"linear-gradient(135deg,#17c394,#12a97f)",color:"#fff",fontWeight:800,fontSize:38,display:"grid",placeItems:"center",boxShadow:"0 0 0 9px #fff,0 12px 34px #17c39488",transform:"scale("+pulse+")"}}>N</div>
  {live.map(p=>{const t=clamp((frame-p.f0)/24,0,1);const e=Easing.inOut(Easing.cubic)(t);const c=CEN(p.ph);const a=p.who==="ai"?HUB:c,b=p.who==="ai"?c:HUB;const x=a.x+(b.x-a.x)*e,y=a.y+(b.y-a.y)*e-Math.sin(e*Math.PI)*26;
   return <div key={p.id} style={{position:"absolute",left:x-14,top:y-14,width:28,height:28,borderRadius:"50%",background:p.who==="ai"?"#17c394":(store.s.people[p.ph-1]||{}).c||"#66b8ff",border:"4px solid #fff",boxShadow:"0 4px 14px rgba(20,40,32,.3)",opacity:t<0.9?1:(1-t)*10}}/>})}
  {s.parcel&&(()=>{const t=clamp((frame-s.parcel.f0)/48,0,1);if(frame<s.parcel.f0||t>=1)return null;const a=CEN(s.parcel.frm),b=CEN(1),e=Easing.inOut(Easing.quad)(t);return <div style={{position:"absolute",left:a.x+(b.x-a.x)*e-20,top:a.y+(b.y-a.y)*e-20-Math.sin(e*Math.PI)*60,fontSize:40,transform:"rotate("+(Math.sin(t*12)*12)+"deg) scale("+(1+Math.sin(e*Math.PI)*0.3)+")"}}>{"📦"}</div>})()}
 </AbsoluteFill>}

let root=null;
function mount(el,people){
 if(root){try{root.unmount()}catch(e){}root=null}
 store.s.people=people;store.ref=React.createRef();
 root=createRoot(el);
 root.render(<Player ref={store.ref} component={Scene} durationInFrames={1800} compositionWidth={W} compositionHeight={H} fps={30} loop autoPlay controls={false} clickToPlay={false} acknowledgeRemotionLicense style={{width:"100%",borderRadius:16,boxShadow:"0 16px 40px rgba(20,40,32,.18)"}}/>);
}
window.NMApt={
 mount,
 say(k,who,text){const t=String(text);U(k).say={who,text:t.length>130?t.slice(0,127)+"…":t,f0:nowF()};U(k).typing=false;emit()},
 typing(k,on){U(k).typing=!!on;emit()},
 status(map){Object.keys(map).forEach(k=>{Object.assign(U(+k),map[k])});emit()},
 env(e){Object.assign(store.s,e);emit()},
 busy(b){store.s.busy=!!b;emit()},
 ping(k,who){const f=nowF();store.s.packets=store.s.packets.filter(p=>f-p.f0<40);store.s.packets.push({id:Math.random(),ph:k,who,f0:f});emit()},
 parcel(frm){store.s.parcel={frm,f0:nowF()};emit()},
 clear(){store.s.units={};store.s.packets=[];store.s.parcel=null;emit()}
};
