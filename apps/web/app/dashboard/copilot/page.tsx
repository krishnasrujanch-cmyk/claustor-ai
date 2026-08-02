"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { contracts as contractsAPI, getToken } from "@/lib/api";
import { Contract } from "@/lib/api";
import { ChevronDown, Send, Copy, Check, RotateCcw, AlertTriangle, CheckCircle, Shield, DollarSign, BookOpen, FileText } from "lucide-react";

const API = "http://localhost:8000";
const C = {
  primary:"#0066FF", primaryLight:"#E6F0FF", accent:"#00A3FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  success:"#22C55E", warning:"#F59E0B", error:"#EF4444",
};

const PROMPT_SUBTITLES: Record<string,[string,string][]> = {
  risk: [
    ["What are the high-risk clauses?",     "Extract liability exclusions, penalties and breach terms"],
    ["What is the liability cap?",          "Check financial exposure limits across contracts"],
    ["Are there indemnification issues?",   "Identify unbudgeted third-party indemnity obligations"],
    ["What penalty clauses exist?",         "Review SLA breach penalties and liquidated damages"],
  ],
  financial: [
    ["What are the payment terms?",         "Net days, milestones, and invoice conditions"],
    ["Are there hidden fees?",              "Identify unexpected costs and escalation clauses"],
    ["What is the total contract value?",   "Aggregate value across all contract tiers"],
    ["What royalties are owed?",            "Review royalty rates, reporting, and audit rights"],
  ],
  legal: [
    ["Who are the contracting parties?",    "Names, roles, and signatory authority"],
    ["What is the governing law?",          "Jurisdiction and dispute resolution forum"],
    ["What are the termination conditions?","Notice periods, for-cause and convenience terms"],
    ["Is there an auto-renewal clause?",    "Review evergreen provisions and opt-out windows"],
  ],
  ip: [
    ["Who owns the intellectual property?", "Ownership, assignment, and work-for-hire terms"],
    ["What data sharing is permitted?",     "Data use, processing, and cross-border transfer"],
    ["Are there exclusivity clauses?",      "Scope, territory, and duration of exclusivity"],
    ["What are the non-compete terms?",     "Restrictions on competitive activity post-term"],
  ],
};

const PROMPT_TABS = [
  { key:"risk",      label:"Risk",      Icon:AlertTriangle, color:"#EF4444",
    prompts:["What are the high-risk clauses?","What is the liability cap?","Are there indemnification issues?","What penalty clauses exist?"]},
  { key:"financial", label:"Financial", Icon:DollarSign, color:"#F59E0B",
    prompts:["What are the payment terms?","Are there hidden fees?","What is the total contract value?","What royalties are owed?"]},
  { key:"legal",     label:"Legal",     Icon:BookOpen,   color:"#8B5CF6",
    prompts:["Who are the contracting parties?","What is the governing law?","What are the termination conditions?","Is there an auto-renewal clause?"]},
  { key:"ip",        label:"IP & Data", Icon:Shield,     color:"#0066FF",
    prompts:["Who owns the intellectual property?","What data sharing is permitted?","Are there exclusivity clauses?","What are the non-compete terms?"]},
];

function getFollowUps(query: string): string[] {
  const q = query.toLowerCase();
  if (q.includes("risk")||q.includes("liabilit")) return ["Draft risk mitigation clauses","Compare against standard playbook","What remedies are available?"];
  if (q.includes("payment")||q.includes("financ")) return ["What happens if payment is late?","Are there dispute resolution clauses?","Summarise all financial obligations"];
  if (q.includes("ip")||q.includes("intellectual")) return ["Who retains IP after termination?","Are there patent licensing terms?","What are the IP transfer conditions?"];
  if (q.includes("terminat")) return ["What notice period is required?","Are there early termination penalties?","What obligations survive termination?"];
  return ["Summarise key risks","What clauses need negotiation?","What are the key dates and deadlines?"];
}

// Render text with [N] citations as styled chips + basic markdown
function RichText({ text, citations }: { text: string; citations?: any[] }) {
  const lines = text.split("\n");
  return (
    <div>
      {lines.map((line, li) => {
        if (!line.trim()) return <div key={li} style={{height:6}}/>;

        // Detect numbered list item
        const numMatch = line.match(/^(\d+)\.\s+(.+)$/);
        if (numMatch) {
          const num     = numMatch[1];
          const noStars = numMatch[2].replace(/\*\*/g, "");
          const colonIdx = noStars.indexOf(":");
          const titleRaw = colonIdx > 0 ? noStars.slice(0, colonIdx) : noStars;
          const rest     = colonIdx > 0 ? noStars.slice(colonIdx + 1).trim() : "";
          const title    = titleRaw.replace(/\[\d+[^\]]*\]/g, "").trim();
          const riskMatch = noStars.match(/\b(HIGH|MEDIUM|LOW)\b/i);
          const risk = riskMatch ? riskMatch[1].toLowerCase() : undefined;
                    const riskColor = risk==="high"?C.error:risk==="medium"?C.warning:risk==="low"?C.success:null;
          const riskBg    = risk==="high"?"#FEF2F2":risk==="medium"?"#FFFBEB":risk==="low"?"#F0FDF4":"transparent";

          return (
            <div key={li} style={{display:"flex",gap:10,marginBottom:10,alignItems:"flex-start"}}>
              <span style={{width:22,height:22,borderRadius:"50%",background:C.primary,
                color:"white",fontSize:10,fontWeight:700,flexShrink:0,
                display:"flex",alignItems:"center",justifyContent:"center",marginTop:1}}>
                {num}
              </span>
              <div style={{flex:1,background:C.bg,border:`1px solid ${riskColor||C.border}`,
                borderLeft:`3px solid ${riskColor||C.primary}`,
                borderRadius:"0 8px 8px 0",padding:"8px 12px"}}>
                <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:rest?4:0,flexWrap:"wrap"}}>
                  <span style={{fontSize:13,fontWeight:700,color:C.heading}}>{inlineParse(title,citations)}</span>
                  {riskColor && (
                    <span style={{fontSize:10,fontWeight:700,padding:"2px 7px",borderRadius:20,
                      background:riskBg,color:riskColor,border:`1px solid ${riskColor}30`,whiteSpace:"nowrap"}}>
                      {risk!.toUpperCase()} RISK
                    </span>
                  )}
                </div>
                {rest && <div style={{fontSize:12,color:C.muted,lineHeight:1.6}}>{inlineParse(rest,citations)}</div>}
              </div>
            </div>
          );
        }

        // Bullet
        const bulletMatch = line.match(/^[-•*]\s+(.+)/);
        if (bulletMatch) return (
          <div key={li} style={{display:"flex",gap:8,marginBottom:4,fontSize:13,color:C.body,lineHeight:1.6}}>
            <span style={{color:C.primary,fontWeight:700,flexShrink:0}}>•</span>
            <span>{inlineParse(bulletMatch[1],citations)}</span>
          </div>
        );

        // Heading
        const hMatch = line.match(/^#{1,3}\s+(.+)/);
        if (hMatch) return (
          <div key={li} style={{fontSize:14,fontWeight:700,color:C.heading,margin:"10px 0 5px"}}>
            {hMatch[1]}
          </div>
        );

        // Normal line
        return (
          <p key={li} style={{margin:"0 0 5px",fontSize:13,color:C.body,lineHeight:1.7}}>
            {inlineParse(line,citations)}
          </p>
        );
      })}
    </div>
  );
}

function inlineParse(text: string, citations?: any[]): React.ReactNode {
  // Split on [N] citations and **bold**
  const parts = text.split(/(\[\d+\]|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (/^\[\d+\]$/.test(part)) {
      const idx = parseInt(part.slice(1,-1));
      const chunk = citations?.find(c=>c.index===idx);
      return <CitChip key={i} idx={idx} chunk={chunk}/>;
    }
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      return <strong key={i} style={{fontWeight:700,color:C.heading}}>{part.slice(2,-2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

function CitChip({ idx, chunk }: { idx:number; chunk?:any }) {
  const [hover, setHover] = useState(false);
  return (
    <span style={{position:"relative",display:"inline-block"}}>
      <span
        onMouseEnter={()=>setHover(true)}
        onMouseLeave={()=>setHover(false)}
        style={{fontSize:10,fontWeight:700,padding:"1px 6px",borderRadius:20,
          background:hover?"#0066FF":C.primaryLight,color:hover?"white":C.primary,
          border:`1px solid ${C.primary}30`,cursor:"pointer",
          verticalAlign:"super",lineHeight:1.2,transition:"all 0.15s",margin:"0 1px"}}>
        [{idx}]
      </span>
      {hover && chunk?.text && (
        <div style={{position:"absolute",bottom:"130%",left:"50%",transform:"translateX(-50%)",
          width:240,zIndex:999,background:"#0A1128",color:"white",borderRadius:8,
          padding:"10px 12px",fontSize:11,lineHeight:1.5,
          boxShadow:"0 8px 24px rgba(0,0,0,0.25)",pointerEvents:"none"}}>
          <div style={{fontSize:9,color:"#94A3B8",marginBottom:3,fontWeight:700,textTransform:"uppercase"}}>
            {chunk.clause_type?.replace(/_/g," ")||"clause"}
          </div>
          {chunk.text.slice(0,160)}...
          <div style={{position:"absolute",top:"100%",left:"50%",transform:"translateX(-50%)",
            borderLeft:"6px solid transparent",borderRight:"6px solid transparent",
            borderTop:"6px solid #0A1128"}}/>
        </div>
      )}
    </span>
  );
}

interface Msg { role:"user"|"assistant"; content:string; citations?:any[]; groundedness?:number; tokens?:number; isStreaming?:boolean; error?:boolean; }

export default function CopilotPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [sel, setSel]             = useState("");
  const [selName, setSelName]     = useState("All contracts");
  const [messages, setMessages]   = useState<Msg[]>([]);
  const [input, setInput]         = useState("");
  const [tab, setTab]             = useState("risk");
  const [loading, setLoading]     = useState(false);
  const [dropdown, setDropdown]   = useState(false);
  const [copied, setCopied]       = useState<number|null>(null);
  const abortRef  = useRef<AbortController|null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(()=>{ contractsAPI.list({page:1,page_size:50}).then(d=>setContracts((d as any).contracts||[])); },[]);
  useEffect(()=>{ bottomRef.current?.scrollIntoView({behavior:"smooth"}); },[messages]);

  const send = useCallback(async(query:string)=>{
    if(!query.trim()||loading) return;
    setInput(""); setLoading(true);
    setMessages(prev=>[...prev,{role:"user",content:query},{role:"assistant",content:"",isStreaming:true}]);
    abortRef.current?.abort();
    const abort = new AbortController(); abortRef.current = abort;
    try {
      const token = getToken();
      const res = await fetch(`${API}/api/v1/chat/stream`,{
        method:"POST",
        headers:{"Authorization":`Bearer ${token}`,"Content-Type":"application/json"},
        body:JSON.stringify({query,contract_id:sel||null}),
        signal:abort.signal,
      });
      if(!res.ok) {
        let errMsg = `HTTP ${res.status}`;
        try {
          const errData = await res.json();
          errMsg = errData.detail || errMsg;
        } catch {}
        if(res.status === 429) {
          setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",
            content:"⚠️ You've reached your monthly AI query limit. Please upgrade your plan to continue.",
            isStreaming:false,error:true};return u;});
          return;
        }
        throw new Error(errMsg);
      }
      const reader=res.body!.getReader(); const dec=new TextDecoder();
      let full="",cits:any[]=[],ground:number|undefined,toks:number|undefined;
      while(true){
        const{done,value}=await reader.read(); if(done) break;
        for(const line of dec.decode(value,{stream:true}).split("\n")){
          if(!line.startsWith("data: ")) continue;
          try{
            const d=JSON.parse(line.slice(6));
            if(d.type==="token"){full+=d.content;setMessages(prev=>{const u=[...prev];u[u.length-1]={...u[u.length-1],content:full,isStreaming:true};return u;});}
            else if(d.type==="citations") cits=d.citations||[];
            else if(d.type==="meta"){ground=d.groundedness;toks=d.tokens;}
            else if(d.type==="done"){setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:full,citations:cits,groundedness:ground,tokens:toks,isStreaming:false};return u;});}
            else if(d.type==="error"){setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:d.message||"Error",isStreaming:false,error:true};return u;});}
          }catch{}
        }
      }
    }catch(err:any){
      if(err.name==="AbortError") return;
      try{
        const r=await fetch(`${API}/api/v1/chat/`,{method:"POST",headers:{"Authorization":`Bearer ${getToken()}`,"Content-Type":"application/json"},body:JSON.stringify({query,contract_id:sel||null})});
        const d=await r.json();
        setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:d.answer||"Error",citations:d.citations||[],isStreaming:false};return u;});
      }catch{setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:"Connection error.",isStreaming:false,error:true};return u;});}
    }finally{setLoading(false);}
  },[sel,loading]);

  return (
    <div style={{height:"calc(100vh - 64px)",display:"flex",flexDirection:"column",background:C.bg}}>

      {/* Header */}
      <div style={{padding:"10px 20px",background:C.surface,borderBottom:`1px solid ${C.border}`,display:"flex",alignItems:"center",gap:10,flexShrink:0}}>
        <div style={{width:30,height:30,borderRadius:"50%",background:`conic-gradient(from 0deg,${C.primary},${C.accent},#A855F7)`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:12,fontWeight:900,color:"white",flexShrink:0}}>✦</div>
        <span style={{fontSize:15,fontWeight:700,color:C.heading,flex:1}}>AI Copilot</span>

        {/* Contract selector */}
        <div style={{position:"relative"}}>
          <button onClick={()=>setDropdown(!dropdown)}
            style={{display:"flex",alignItems:"center",gap:6,padding:"6px 12px",border:`1px solid ${C.border}`,borderRadius:8,background:sel?C.primaryLight:C.surface,cursor:"pointer",fontSize:12,color:sel?C.primary:C.body}}>
            <FileText size={11}/><span style={{maxWidth:150,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{selName}</span><ChevronDown size={11}/>
          </button>
          {dropdown && (
            <div style={{position:"absolute",right:0,top:36,width:260,background:C.surface,border:`1px solid ${C.border}`,borderRadius:10,boxShadow:"0 8px 24px rgba(0,0,0,0.1)",zIndex:100,maxHeight:260,overflowY:"auto"}}>
              <div onClick={()=>{setSel("");setSelName("All contracts");setDropdown(false);}} style={{padding:"9px 14px",cursor:"pointer",fontSize:12,background:!sel?C.primaryLight:"white",color:!sel?C.primary:C.body}}>All contracts</div>
              {contracts.map(c=>(
                <div key={c.id} onClick={()=>{setSel(c.id);setSelName(c.title);setDropdown(false);}}
                  style={{padding:"9px 14px",cursor:"pointer",fontSize:12,background:sel===c.id?C.primaryLight:"white",color:sel===c.id?C.primary:C.body,borderTop:`1px solid ${C.border}`,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                  {c.title}
                </div>
              ))}
            </div>
          )}
        </div>
        {messages.length>0 && <button onClick={()=>{setMessages([]);abortRef.current?.abort();}} style={{padding:"5px 10px",border:`1px solid ${C.border}`,borderRadius:8,background:"none",cursor:"pointer",fontSize:11,color:C.muted}}>Clear</button>}
      </div>

      {/* Messages */}
      <div style={{flex:1,overflowY:"auto",padding:"20px"}}>
        {messages.length===0 && (
          <div style={{maxWidth:560,margin:"0 auto",textAlign:"center",paddingTop:28}}>
            <div style={{width:52,height:52,borderRadius:"50%",margin:"0 auto 14px",background:`conic-gradient(from 0deg,${C.primary},${C.accent},#A855F7)`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:20,color:"white"}}>✦</div>
            <h2 style={{fontSize:19,fontWeight:700,color:C.heading,marginBottom:8}}>What do you want to know?</h2>
            <p style={{fontSize:13,color:C.muted,marginBottom:24}}>Ask about risks, clauses, parties, obligations, or anything in your contracts.</p>
            <div style={{display:"flex",gap:6,justifyContent:"center",marginBottom:12,flexWrap:"wrap"}}>
              {PROMPT_TABS.map(t=>(
                <button key={t.key} onClick={()=>setTab(t.key)}
                  style={{padding:"5px 12px",borderRadius:20,border:"none",cursor:"pointer",fontSize:12,fontWeight:600,background:tab===t.key?t.color:C.bg,color:tab===t.key?"white":C.muted,display:"flex",alignItems:"center",gap:4,transition:"all 0.15s"}}>
                  <t.Icon size={10}/>{t.label}
                </button>
              ))}
            </div>
            <div style={{display:"flex",flexDirection:"column",gap:6}}>
              {PROMPT_TABS.find(t=>t.key===tab)?.prompts.map(p=>(
                <button key={p} onClick={()=>send(p)} style={{padding:"9px 14px",background:C.surface,border:`1px solid ${C.border}`,borderRadius:10,cursor:"pointer",fontSize:13,color:C.body,textAlign:"left",transition:"all 0.15s"}}
                  onMouseEnter={e=>{(e.currentTarget as HTMLElement).style.borderColor=C.primary;(e.currentTarget as HTMLElement).style.color=C.primary;}}
                  onMouseLeave={e=>{(e.currentTarget as HTMLElement).style.borderColor=C.border;(e.currentTarget as HTMLElement).style.color=C.body;}}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{maxWidth:800,margin:"0 auto"}}>
          {messages.map((msg,idx)=>(
            <div key={idx} style={{display:"flex",justifyContent:msg.role==="user"?"flex-end":"flex-start",marginBottom:18,alignItems:"flex-start",gap:8}}>
              {msg.role==="assistant" && (
                <div style={{width:26,height:26,borderRadius:"50%",flexShrink:0,background:`conic-gradient(from 0deg,${C.primary},${C.accent},#A855F7)`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,fontWeight:900,color:"white",marginTop:3}}>✦</div>
              )}
              <div style={{maxWidth:"88%",minWidth:0}}>
                <div style={{padding:msg.role==="user"?"9px 14px":"12px 16px",borderRadius:msg.role==="user"?"12px 12px 2px 12px":"2px 12px 12px 12px",background:msg.role==="user"?C.primary:msg.error?"#FEF2F2":C.surface,color:msg.role==="user"?"white":msg.error?C.error:C.body,border:msg.role==="assistant"?`1px solid ${msg.error?"#EF444330":C.border}`:"none",fontSize:13,lineHeight:1.7}}>
                  {msg.isStreaming ? (
                    <span>{msg.content}<span style={{display:"inline-block",width:6,height:14,background:C.primary,marginLeft:2,verticalAlign:"text-bottom",borderRadius:2,animation:"blink 0.8s infinite"}}/></span>
                  ) : msg.role==="assistant" && !msg.error ? (
                    <RichText text={msg.content} citations={msg.citations}/>
                  ) : (
                    <span style={{whiteSpace:"pre-wrap"}}>{msg.content}</span>
                  )}
                </div>

                {/* Footer */}
                {msg.role==="assistant" && !msg.isStreaming && !msg.error && (
                  <div style={{marginTop:8}}>
                    <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:10,flexWrap:"wrap"}}>
                      {msg.groundedness!==undefined && (
                        <span style={{fontSize:10,fontWeight:700,padding:"2px 8px",borderRadius:20,background:msg.groundedness>=0.9?"#F0FDF4":"#FFFBEB",color:msg.groundedness>=0.9?C.success:C.warning,border:`1px solid ${msg.groundedness>=0.9?C.success:C.warning}30`,display:"inline-flex",alignItems:"center",gap:4}}>
                          <CheckCircle size={9}/> Verified {Math.round(msg.groundedness*100)}%
                        </span>
                      )}
                      {msg.tokens && <span style={{fontSize:10,color:C.muted}}>{msg.tokens.toLocaleString()} tokens</span>}
                      <div style={{marginLeft:"auto",display:"flex",gap:5}}>
                        <button onClick={()=>{navigator.clipboard.writeText(msg.content);setCopied(idx);setTimeout(()=>setCopied(null),2000);}}
                          style={{display:"flex",alignItems:"center",gap:3,padding:"4px 9px",border:`1px solid ${C.border}`,borderRadius:20,background:C.surface,cursor:"pointer",fontSize:11,color:C.muted}}>
                          {copied===idx?<><Check size={9}/>Copied</>:<><Copy size={9}/>Copy</>}
                        </button>
                        <button onClick={()=>{const prev=messages[idx-1];if(prev)send(prev.content);}}
                          style={{display:"flex",alignItems:"center",gap:3,padding:"4px 9px",border:`1px solid ${C.border}`,borderRadius:20,background:C.surface,cursor:"pointer",fontSize:11,color:C.muted}}>
                          <RotateCcw size={9}/>Retry
                        </button>
                      </div>
                    </div>
                    {idx===messages.length-1 && (
                      <div>
                        <div style={{fontSize:10,fontWeight:700,color:C.muted,textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:5}}>Suggested next steps</div>
                        <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
                          {getFollowUps(messages[idx-1]?.content||"").map(q=>(
                            <button key={q} onClick={()=>send(q)}
                              style={{padding:"5px 11px",border:`1px solid ${C.primary}20`,borderRadius:20,background:C.primaryLight,color:C.primary,fontSize:11,fontWeight:600,cursor:"pointer",transition:"all 0.15s"}}
                              onMouseEnter={e=>{(e.currentTarget as HTMLElement).style.background=C.primary;(e.currentTarget as HTMLElement).style.color="white";}}
                              onMouseLeave={e=>{(e.currentTarget as HTMLElement).style.background=C.primaryLight;(e.currentTarget as HTMLElement).style.color=C.primary;}}>
                              {q}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef}/>
        </div>
      </div>

      {/* Input */}
      <div style={{padding:"10px 20px 14px",background:C.surface,borderTop:`1px solid ${C.border}`,flexShrink:0}}>
        <div style={{maxWidth:800,margin:"0 auto",display:"flex",gap:8,alignItems:"flex-end"}}>
          <div style={{flex:1,border:`1.5px solid ${loading?C.primary:C.border}`,borderRadius:12,background:C.surface,overflow:"hidden",transition:"border-color 0.15s"}}>
            <textarea
              value={input} onChange={e=>setInput(e.target.value)}
              onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send(input);}}}
              placeholder={sel ? `Ask about ${selName}...` : "Ask anything about your contracts..."}
              rows={1} disabled={loading}
              style={{width:"100%",padding:"10px 14px",border:"none",fontSize:13,color:C.heading,background:"transparent",resize:"none",outline:"none",fontFamily:"inherit",lineHeight:1.5,maxHeight:120,overflowY:"auto",boxSizing:"border-box"}}
              onInput={e=>{const t=e.currentTarget;t.style.height="auto";t.style.height=Math.min(t.scrollHeight,120)+"px";}}
            />
          </div>
          <button onClick={()=>loading?abortRef.current?.abort():send(input)}
            style={{width:38,height:38,borderRadius:10,border:"none",background:loading?"#FEF2F2":input.trim()?C.primary:"#E2E8F0",color:loading?C.error:input.trim()?"white":C.muted,cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,transition:"all 0.15s"}}>
            {loading?<span style={{fontSize:11,fontWeight:700}}>✕</span>:<Send size={14}/>}
          </button>
        </div>
        <p style={{fontSize:10,color:C.muted,textAlign:"center",marginTop:5}}>AI-powered · Citations verified · Not legal advice</p>
      </div>

      <style>{`@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}`}</style>
    </div>
  );
}
