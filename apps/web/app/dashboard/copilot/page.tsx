"use client";
export const dynamic = "force-dynamic";
import ReactMarkdown from "react-markdown";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, useCallback } from "react";
import { contracts as contractsAPI, getToken } from "@/lib/api";
import { Contract } from "@/lib/api";
import { Send, Copy, Check, RotateCcw, AlertTriangle, CheckCircle, Shield, DollarSign, BookOpen, FileText, Search, X } from "lucide-react";

const API = "http://localhost:8000";
const C = {
  primary:"#0066FF", primaryLight:"#E6F0FF", accent:"#00A3FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#F8FAFC",
  success:"#22C55E", warning:"#F59E0B", error:"#EF4444",
};

// Claustor logo SVG component
function ClauStorMark({ size=20, white=false }: { size?: number; white?: boolean }) {
  const c = white ? "rgba(255,255,255,0.95)" : "#0066FF";
  const c2 = white ? "rgba(255,255,255,0.6)" : "#00A3FF";
  const c3 = white ? "rgba(255,255,255,0.3)" : "rgba(0,102,255,0.2)";
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none">
      <path d="M26 7C23 5 19.5 4 15 4C8.4 4 3 9.4 3 18s5.4 14 12 14c4.5 0 8-1 11-3"
        stroke={c} strokeWidth="3.5" strokeLinecap="round" fill="none"/>
      <circle cx="26" cy="7" r="2.5" fill={c2}/>
      <circle cx="26" cy="29" r="2.5" fill={c2}/>
      <line x1="26" y1="7" x2="32" y2="7" stroke={c2} strokeWidth="1.5"/>
      <circle cx="32" cy="7" r="1.5" fill={c2}/>
      <line x1="26" y1="29" x2="32" y2="29" stroke={c2} strokeWidth="1.5"/>
      <circle cx="32" cy="29" r="1.5" fill={c2}/>
      <rect x="11" y="12" width="10" height="12" rx="1.5"
        fill={c3} stroke={c2} strokeWidth="0.8"/>
      <line x1="13" y1="16" x2="19" y2="16" stroke={c2} strokeWidth="0.8"/>
      <line x1="13" y1="19" x2="19" y2="19" stroke={c2} strokeWidth="0.8"/>
      <line x1="13" y1="22" x2="17" y2="22" stroke={c} strokeWidth="1"/>
    </svg>
  );
}

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

function RichText({ text, citations }: { text: string; citations?: any[] }) {
  // Pre-process: extract and render markdown tables
  const tableRegex = new RegExp("(\\|.+\\|\\n)(\\|[-: |]+\\|\\n)((?:\\|.+\\|(?:\\n)?)*)", "g");
  const parts: Array<{type:"text"|"table"; content:string}> = [];
  let lastIdx = 0;
  let match;
  while ((match = tableRegex.exec(text)) !== null) {
    if (match.index > lastIdx) parts.push({type:"text", content:text.slice(lastIdx, match.index)});
    parts.push({type:"table", content:match[0]});
    lastIdx = match.index + match[0].length;
  }
  if (lastIdx < text.length) parts.push({type:"text", content:text.slice(lastIdx)});

  return (
    <div>
      {parts.map((part, pi) => {
        if (part.type === "table") {
          const rows = part.content.trim().split("\n").filter(r => r.trim() && !r.match(/^\|[-:| ]+\|$/));
          const headers = rows[0].split("|").filter(c => c.trim()).map(c => c.trim());
          const dataRows = rows.slice(1);
          return (
            <div key={pi} style={{overflowX:"auto",marginBottom:12,marginTop:8}}>
              <table style={{borderCollapse:"collapse",width:"100%",fontSize:12}}>
                <thead>
                  <tr>
                    {headers.map((h,i) => (
                      <th key={i} style={{
                        padding:"8px 12px",background:"#0066FF",color:"white",
                        fontWeight:700,textAlign:"left",whiteSpace:"nowrap",
                        border:"1px solid #DBEAFE",
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dataRows.map((row,ri) => {
                    const cells = row.split("|").filter(c => c.trim()).map(c => c.trim());
                    return (
                      <tr key={ri} style={{background:ri%2===0?"white":"#F8FAFC"}}>
                        {cells.map((cell,ci) => (
                          <td key={ci} style={{
                            padding:"7px 12px",border:"1px solid #E5E7EB",
                            color:"#374151",verticalAlign:"top",
                          }}>{inlineParse(cell, citations)}</td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        }
        // Render text part
        const lines = part.content.split("\n");
        return (
          <div key={pi}>
          {lines.map((line, li) => {
        if (!line.trim()) return <div key={li} style={{height:6}}/>;
        const numMatch = line.match(/^(\d+)\.\s+(.+)$/);
        if (numMatch) {
          const num = numMatch[1];
          const noStars = numMatch[2].replace(/\*\*/g, "");
          const colonIdx = noStars.indexOf(":");
          const titleRaw = colonIdx > 0 ? noStars.slice(0, colonIdx) : noStars;
          const rest = colonIdx > 0 ? noStars.slice(colonIdx + 1).trim() : "";
          const title = titleRaw.replace(/\[\d+[^\]]*\]/g, "").trim();
          const riskMatch = noStars.match(/\b(HIGH|MEDIUM|LOW)\b/i);
          const risk = riskMatch ? riskMatch[1].toLowerCase() : undefined;
          const riskColor = risk==="high"?C.error:risk==="medium"?C.warning:risk==="low"?C.success:null;
          const riskBg = risk==="high"?"#FEF2F2":risk==="medium"?"#FFFBEB":risk==="low"?"#F0FDF4":"transparent";
          return (
            <div key={li} style={{display:"flex",gap:10,marginBottom:10,alignItems:"flex-start"}}>
              <span style={{width:22,height:22,borderRadius:"50%",background:C.primary,color:"white",fontSize:10,fontWeight:700,flexShrink:0,display:"flex",alignItems:"center",justifyContent:"center",marginTop:1}}>{num}</span>
              <div style={{flex:1,background:C.bg,border:`1px solid ${riskColor||C.border}`,borderLeft:`3px solid ${riskColor||C.primary}`,borderRadius:"0 8px 8px 0",padding:"8px 12px"}}>
                <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:rest?4:0,flexWrap:"wrap"}}>
                  <span style={{fontSize:13,fontWeight:700,color:C.heading}}>{inlineParse(title,citations)}</span>
                  {riskColor && (
                    <span style={{fontSize:10,fontWeight:700,padding:"2px 7px",borderRadius:20,background:riskBg,color:riskColor,border:`1px solid ${riskColor}30`,whiteSpace:"nowrap"}}>{risk!.toUpperCase()} RISK</span>
                  )}
                </div>
                {rest && <div style={{fontSize:12,color:C.muted,lineHeight:1.6}}>{inlineParse(rest,citations)}</div>}
              </div>
            </div>
          );
        }
        const bulletMatch = line.match(/^[-•*]\s+(.+)/);
        if (bulletMatch) return (
          <div key={li} style={{display:"flex",gap:8,marginBottom:4,fontSize:13,color:C.body,lineHeight:1.6}}>
            <span style={{color:C.primary,fontWeight:700,flexShrink:0}}>•</span>
            <span>{inlineParse(bulletMatch[1],citations)}</span>
          </div>
        );
        const hMatch = line.match(/^#{1,3}\s+(.+)/);
        if (hMatch) return <div key={li} style={{fontSize:14,fontWeight:700,color:C.heading,margin:"10px 0 5px"}}>{hMatch[1]}</div>;
        return <p key={li} style={{margin:"0 0 5px",fontSize:13,color:C.body,lineHeight:1.7}}>{inlineParse(line,citations)}</p>;
      })}
          </div>
        );
      })}
    </div>
  );
}

function inlineParse(text: string, citations?: any[]): React.ReactNode {
  const parts = text.split(/(\[\d+\]|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (/^\[\d+\]$/.test(part)) {
      const idx = parseInt(part.slice(1,-1));
      const chunk = citations?.find(c=>c.index===idx);
      return <CitChip key={i} idx={idx} chunk={chunk}/>;
    }
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={i} style={{fontWeight:700,color:C.heading}}>{part.slice(2,-2)}</strong>;
    return <span key={i}>{part}</span>;
  });
}

function CitChip({ idx, chunk }: { idx:number; chunk?:any }) {
  const [hover, setHover] = useState(false);
  return (
    <span style={{position:"relative",display:"inline-block"}}>
      <span onMouseEnter={()=>setHover(true)} onMouseLeave={()=>setHover(false)}
        style={{fontSize:10,fontWeight:700,padding:"1px 6px",borderRadius:20,
          background:hover?"#0066FF":C.primaryLight,color:hover?"white":C.primary,
          border:`1px solid ${C.primary}30`,cursor:"pointer",verticalAlign:"super",
          lineHeight:1.2,transition:"all 0.15s",margin:"0 1px"}}>
        [{idx}]
      </span>
      {hover && chunk?.text && (
        <span style={{position:"absolute",bottom:"130%",left:"50%",transform:"translateX(-50%)",
          width:240,zIndex:999,background:"#0A1128",color:"white",borderRadius:8,
          padding:"10px 12px",fontSize:11,lineHeight:1.5,display:"block",
          boxShadow:"0 8px 24px rgba(0,0,0,0.25)",pointerEvents:"none"}}>
          <span style={{display:"block",fontSize:9,color:"#94A3B8",marginBottom:3,fontWeight:700,textTransform:"uppercase"}}>{chunk.clause_type?.replace(/_/g," ")||"clause"}</span>
          {chunk.text.slice(0,160)}...
          <span style={{position:"absolute",top:"100%",left:"50%",transform:"translateX(-50%)",display:"block",
            borderLeft:"6px solid transparent",borderRight:"6px solid transparent",borderTop:"6px solid #0A1128"}}/>
        </span>
      )}
    </span>
  );
}

// Typing indicator
function TypingDots() {
  return (
    <span style={{display:"inline-flex",gap:3,alignItems:"center",padding:"2px 0"}}>
      {[0,1,2].map(i=>(
        <span key={i} style={{width:6,height:6,borderRadius:"50%",background:C.primary,opacity:0.4,
          animation:`typingDot 1.2s ease-in-out ${i*0.2}s infinite`}}/>
      ))}
    </span>
  );
}

// Searchable contract dropdown
function ContractDropdown({ contracts, sel, selName, onSelect }: {
  contracts: Contract[]; sel: string; selName: string;
  onSelect: (id: string, name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
    else setSearch("");
  }, [open]);

  const filtered = contracts.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase()) ||
    (c.counterparty || "").toLowerCase().includes(search.toLowerCase())
  );

  const riskColor = (level: string) =>
    level==="high"?C.error:level==="medium"?C.warning:level==="low"?C.success:C.muted;

  return (
    <div ref={ref} style={{position:"relative"}}>
      <button onClick={()=>setOpen(!open)}
        style={{display:"flex",alignItems:"center",gap:6,padding:"6px 12px",
          border:`1px solid ${open?C.primary:C.border}`,borderRadius:8,
          background:sel
            ? "rgba(0,102,255,0.06)"
            : "white",
          backdropFilter:"blur(8px)",
          cursor:"pointer",fontSize:12,
          color:sel?C.primary:C.body,
          transition:"all 0.15s",
          boxShadow:open?"0 0 0 3px rgba(0,102,255,0.1)":"none"}}>
        <FileText size={11}/>
        <span style={{maxWidth:150,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{selName}</span>
        <span style={{marginLeft:2,color:C.muted,fontSize:10,transform:open?"rotate(180deg)":"none",transition:"transform 0.15s",display:"inline-block"}}>▼</span>
      </button>

      {open && (
        <div style={{position:"absolute",right:0,top:36,width:280,
          background:"rgba(255,255,255,0.95)",backdropFilter:"blur(12px)",
          border:`1px solid ${C.border}`,borderRadius:12,
          boxShadow:"0 12px 32px rgba(0,0,0,0.12)",zIndex:200}}>

          {/* Search */}
          <div style={{padding:"8px 10px",borderBottom:`1px solid ${C.border}`}}>
            <div style={{display:"flex",alignItems:"center",gap:6,
              background:C.bg,borderRadius:7,padding:"5px 10px",
              border:`1px solid ${C.border}`}}>
              <Search size={11} color={C.muted}/>
              <input ref={inputRef} value={search} onChange={e=>setSearch(e.target.value)}
                placeholder="Search contracts..."
                style={{border:"none",background:"transparent",fontSize:12,
                  color:C.body,outline:"none",width:"100%",fontFamily:"inherit"}}/>
              {search && (
                <button onClick={()=>setSearch("")}
                  style={{background:"none",border:"none",cursor:"pointer",padding:0,display:"flex"}}>
                  <X size={10} color={C.muted}/>
                </button>
              )}
            </div>
          </div>

          {/* Options */}
          <div style={{maxHeight:240,overflowY:"auto"}}>
            <div onClick={()=>{onSelect("","All contracts");setOpen(false);}}
              style={{padding:"9px 14px",cursor:"pointer",fontSize:12,
                background:!sel?"rgba(0,102,255,0.06)":"transparent",
                color:!sel?C.primary:C.body,
                display:"flex",alignItems:"center",gap:8,
                transition:"background 0.1s"}}
              onMouseEnter={e=>(e.currentTarget as HTMLElement).style.background=!sel?"rgba(0,102,255,0.08)":"#F8FAFC"}
              onMouseLeave={e=>(e.currentTarget as HTMLElement).style.background=!sel?"rgba(0,102,255,0.06)":"transparent"}>
              <span style={{fontSize:11}}>🌐</span>
              <span style={{fontWeight:!sel?600:400}}>All contracts</span>
            </div>
            {filtered.length === 0 && (
              <div style={{padding:"16px 14px",fontSize:12,color:C.muted,textAlign:"center"}}>
                No contracts found
              </div>
            )}
            {filtered.map(c=>(
              <div key={c.id} onClick={()=>{onSelect(c.id,c.title);setOpen(false);}}
                style={{padding:"9px 14px",cursor:"pointer",fontSize:12,
                  background:sel===c.id?"rgba(0,102,255,0.06)":"transparent",
                  borderTop:`1px solid ${C.border}`,transition:"background 0.1s"}}
                onMouseEnter={e=>(e.currentTarget as HTMLElement).style.background=sel===c.id?"rgba(0,102,255,0.08)":"#F8FAFC"}
                onMouseLeave={e=>(e.currentTarget as HTMLElement).style.background=sel===c.id?"rgba(0,102,255,0.06)":"transparent"}>
                <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:2}}>
                  <span style={{flex:1,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",
                    fontWeight:sel===c.id?600:400,color:sel===c.id?C.primary:C.heading}}>
                    {c.title}
                  </span>
                  {(c as any).risk_level && (
                    <span style={{fontSize:9,fontWeight:700,padding:"1px 5px",borderRadius:10,
                      background:riskColor((c as any).risk_level)+"15",
                      color:riskColor((c as any).risk_level),flexShrink:0}}>
                      {(c as any).risk_level.toUpperCase()}
                    </span>
                  )}
                </div>
                {(c as any).counterparty && (
                  <div style={{fontSize:10,color:C.muted,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                    {(c as any).counterparty}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div style={{padding:"6px 10px",borderTop:`1px solid ${C.border}`,
            fontSize:10,color:C.muted,textAlign:"center"}}>
            {filtered.length} contract{filtered.length!==1?"s":""} {search?"found":"total"}
          </div>
        </div>
      )}
    </div>
  );
}

interface Msg {
  role:"user"|"assistant"; content:string; citations?:any[];
  groundedness?:number; tokens?:number; isStreaming?:boolean;
  error?:boolean; db_sourced?:boolean;
}

function CopilotPageInner() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [sel, setSel]             = useState("");
  const [selName, setSelName]     = useState("All contracts");
  const [messages, setMessages]   = useState<Msg[]>([]);
  const [input, setInput]         = useState("");
  const [tab, setTab]             = useState("risk");
  const [conversationId, setConversationId] = useState<string|null>(null);
  const [suggestedContract, setSuggestedContract] = useState<string|null>(null);
  const [loading, setLoading]     = useState(false);
  const [dynamicTabs, setDynamicTabs] = useState<any[]>([]);
  const [promptsLoading, setPromptsLoading] = useState(false);
  const [copied, setCopied]       = useState<number|null>(null);
  const abortRef  = useRef<AbortController|null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(()=>{
    (async()=>{
      let all:Contract[]=[],page=1;
      while(true){
        const d:any=await contractsAPI.list({page,page_size:100});
        const batch=d.contracts||[];
        all=[...all,...batch];
        if(batch.length<100)break;
        page++;
      }
      setContracts(all);
    })();
  },[]);
  useEffect(()=>{ bottomRef.current?.scrollIntoView({behavior:"smooth"}); },[messages]);

  // Auto-submit query from ⌘K command palette (?q= param)
  const searchParams = useSearchParams();
  const lastAutoQueryRef = useRef("");
  useEffect(()=>{
    const q = searchParams?.get("q");
    if (!q || q === lastAutoQueryRef.current) return;
    lastAutoQueryRef.current = q;
    // Clear param from URL without reload
    const url = new URL(window.location.href);
    url.searchParams.delete("q");
    window.history.replaceState({}, "", url.toString());
    // Send after short delay
    setTimeout(()=>{ send(q); }, 400);
  }, [searchParams]);

  useEffect(()=>{
    setPromptsLoading(true);
    const url = sel
      ? `${API}/api/v1/chat/suggested-prompts?contract_id=${sel}`
      : `${API}/api/v1/chat/suggested-prompts`;
    fetch(url,{headers:{"Authorization":`Bearer ${getToken()}`}})
      .then(r=>r.json())
      .then(d=>{ if(d.tabs?.length) setDynamicTabs(d.tabs); })
      .catch(()=>{})
      .finally(()=>setPromptsLoading(false));
  },[sel]);

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
        body:JSON.stringify({query,contract_id:sel||null,conversation_id:conversationId}),
        signal:abort.signal,
      });
      if(!res.ok) {
        let errMsg = `HTTP ${res.status}`;
        try { const errData = await res.json(); errMsg = errData.detail || errMsg; } catch {}
        if(res.status === 429) {
          setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",
            content:"⚠️ You've reached your monthly AI query limit. Please upgrade your plan to continue.",
            isStreaming:false,error:true};return u;});
          return;
        }
        throw new Error(errMsg);
      }
      const reader=res.body!.getReader(); const dec=new TextDecoder();
      let full="",cits:any[]=[],ground:number|undefined,toks:number|undefined,dbSourced=false;
      while(true){
        const{done,value}=await reader.read(); if(done) break;
        for(const line of dec.decode(value,{stream:true}).split("\n")){
          if(!line.startsWith("data: ")) continue;
          try{
            const d=JSON.parse(line.slice(6));
            if(d.type==="token"){full+=d.content;setMessages(prev=>{const u=[...prev];u[u.length-1]={...u[u.length-1],content:full,isStreaming:true};return u;});}
            else if(d.type==="citations") cits=d.citations||[];
            else if(d.type==="meta"){
              if(d.db_sourced){dbSourced=true;setMessages(prev=>{const u=[...prev];u[u.length-1]={...u[u.length-1],db_sourced:true,groundedness:1,isStreaming:false};return u;});}
              ground=d.groundedness;toks=d.tokens;
            }
            else if(d.type==="done"){setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:full,citations:cits,groundedness:ground,tokens:toks,isStreaming:false,db_sourced:dbSourced};return u;});}
            else if(d.type==="conversation_id"){setConversationId(d.conversation_id);}
            else if(d.type==="contract_context" && !sel && d.contract_id){setSuggestedContract(d.contract_id);}
            else if(d.type==="error"){setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:d.message||"Error",isStreaming:false,error:true};return u;});}
          }catch{}
        }
      }
    }catch(err:any){
      if(err.name==="AbortError") return;
      try{
        const r=await fetch(`${API}/api/v1/chat/`,{method:"POST",headers:{"Authorization":`Bearer ${getToken()}`,"Content-Type":"application/json"},body:JSON.stringify({query,contract_id:sel||null,conversation_id:conversationId})});
        const d=await r.json();
        setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:d.answer||"Error",citations:d.citations||[],isStreaming:false};return u;});
      }catch{setMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:"Connection error.",isStreaming:false,error:true};return u;});}
    }finally{setLoading(false);}
  },[sel,loading,conversationId]);

  return (
    <div style={{height:"calc(100vh - 64px)",display:"flex",flexDirection:"column",background:C.bg}}>

      {/* Header */}
      <div style={{padding:"10px 20px",background:"rgba(255,255,255,0.8)",backdropFilter:"blur(12px)",
        borderBottom:`1px solid ${C.border}`,display:"flex",alignItems:"center",gap:10,flexShrink:0}}>
        <div style={{width:30,height:30,borderRadius:9,background:"white",border:"1.5px solid rgba(0,102,255,0.2)",
          display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,
          boxShadow:"0 2px 8px rgba(0,102,255,0.15)"}}>
          <ClauStorMark size={18}/>
        </div>
        <span style={{fontSize:15,fontWeight:700,color:C.heading,flex:1}}>AI Copilot</span>
              {(()=>{
                try {
                  const p = JSON.parse(atob((localStorage.getItem("token")||"").split(".")[1]||"e30="));
                  if(p.role === "viewer") return (
                    <span style={{
                      fontSize:11,fontWeight:700,
                      background:"#FEF3C7",color:"#92400E",
                      border:"1px solid #FDE68A",
                      padding:"2px 10px",borderRadius:20,
                      display:"inline-flex",alignItems:"center",gap:4,
                    }}>
                      🔒 Viewer Mode — Some data restricted
                    </span>
                  );
                } catch {}
                return null;
              })()}

        {suggestedContract && !sel && (
          <div style={{background:"rgba(0,102,255,0.06)",border:"1px solid rgba(0,102,255,0.2)",
            borderRadius:8,padding:"6px 12px",display:"flex",alignItems:"center",gap:8,fontSize:12}}>
            <span style={{color:"#1D4ED8"}}>💡 Focus on this contract?</span>
            <button onClick={()=>{setSel(suggestedContract);setSuggestedContract(null);}}
              style={{background:"rgba(0,102,255,0.1)",backdropFilter:"blur(8px)",color:C.primary,
                border:"1px solid rgba(0,102,255,0.2)",borderRadius:6,padding:"3px 10px",
                cursor:"pointer",fontSize:11,fontWeight:700}}>
              Focus
            </button>
            <button onClick={()=>setSuggestedContract(null)}
              style={{background:"none",border:"none",cursor:"pointer",display:"flex",padding:0}}>
              <X size={12} color={C.muted}/>
            </button>
          </div>
        )}

        <ContractDropdown
          contracts={contracts} sel={sel} selName={selName}
          onSelect={(id,name)=>{setSel(id);setSelName(name);}}
        />

        {messages.length>0 && (
          <button onClick={()=>{setMessages([]);abortRef.current?.abort();}}
            style={{padding:"5px 10px",border:`1px solid ${C.border}`,borderRadius:8,
              background:"rgba(255,255,255,0.6)",backdropFilter:"blur(8px)",
              cursor:"pointer",fontSize:11,color:C.muted,transition:"all 0.15s"}}
            onMouseEnter={e=>(e.currentTarget as HTMLElement).style.borderColor=C.primary}
            onMouseLeave={e=>(e.currentTarget as HTMLElement).style.borderColor=C.border}>
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div style={{flex:1,overflowY:"auto",padding:"20px"}}>
        {messages.length===0 && (
          <div style={{maxWidth:560,margin:"0 auto",textAlign:"center",paddingTop:28}}>
            <div style={{width:56,height:56,borderRadius:16,margin:"0 auto 14px",
              background:"white",border:"2px solid rgba(0,102,255,0.15)",
              display:"flex",alignItems:"center",justifyContent:"center",
              boxShadow:"0 8px 24px rgba(0,102,255,0.12)"}}>
              <ClauStorMark size={32}/>
            </div>
            <h2 style={{fontSize:19,fontWeight:700,color:C.heading,marginBottom:8}}>What do you want to know?</h2>
            <p style={{fontSize:13,color:C.muted,marginBottom:24}}>Ask about risks, clauses, parties, obligations, or anything in your contracts.</p>
            <div style={{display:"flex",gap:6,justifyContent:"center",marginBottom:12,flexWrap:"wrap"}}>
              {(dynamicTabs.length?dynamicTabs.map((t:any)=>({...t,Icon:PROMPT_TABS.find(p=>p.key===t.key)?.Icon||FileText,color:PROMPT_TABS.find(p=>p.key===t.key)?.color||C.primary,prompts:t.prompts?.map((p:any)=>p.question||p)})):PROMPT_TABS).map((t:any)=>(
                <button key={t.key} onClick={()=>setTab(t.key)}
                  style={{padding:"5px 14px",borderRadius:20,cursor:"pointer",fontSize:12,fontWeight:600,
                    background:tab===t.key?t.color:"rgba(255,255,255,0.7)",
                    backdropFilter:"blur(8px)",
                    color:tab===t.key?"white":C.muted,
                    border:tab===t.key?"none":`1px solid ${C.border}`,
                    display:"flex",alignItems:"center",gap:4,transition:"all 0.15s",
                    boxShadow:tab===t.key?`0 4px 12px ${t.color}40`:"none"}}>
                  <t.Icon size={10}/>{t.label}
                </button>
              ))}
            </div>
            <div style={{display:"flex",flexDirection:"column",gap:6}}>
              {promptsLoading && (
                <div style={{textAlign:"center",padding:"20px",color:C.muted,fontSize:12}}>
                  Generating questions for this contract...
                </div>
              )}
              {!promptsLoading && (dynamicTabs.length?dynamicTabs:PROMPT_TABS).find((t:any)=>t.key===tab)?.prompts?.map((p:any,i:number)=>{
                const question = typeof p === "string" ? p : p.question;
                const sub = typeof p === "string" ? (PROMPT_SUBTITLES[tab]?.[i]?.[1]||"") : (p.subtitle||"");
                return (
                  <button key={question} onClick={()=>send(question)}
                    style={{padding:"10px 14px",background:"rgba(255,255,255,0.7)",
                      backdropFilter:"blur(8px)",
                      border:`1px solid ${C.border}`,borderRadius:10,cursor:"pointer",
                      textAlign:"left",transition:"all 0.15s",
                      boxShadow:"0 1px 3px rgba(0,0,0,0.04)"}}
                    onMouseEnter={e=>{
                      (e.currentTarget as HTMLElement).style.borderColor=C.primary;
                      (e.currentTarget as HTMLElement).style.background="rgba(0,102,255,0.04)";
                    }}
                    onMouseLeave={e=>{
                      (e.currentTarget as HTMLElement).style.borderColor=C.border;
                      (e.currentTarget as HTMLElement).style.background="rgba(255,255,255,0.7)";
                    }}>
                    <div style={{fontSize:13,color:C.heading,fontWeight:500,marginBottom:2}}>{question}</div>
                    {sub && <div style={{fontSize:11,color:C.muted}}>{sub}</div>}
                  </button>
                );
              })
}
            </div>
          </div>
        )}

        <div style={{maxWidth:800,margin:"0 auto"}}>
          {messages.map((msg,idx)=>(
            <div key={idx} style={{display:"flex",justifyContent:msg.role==="user"?"flex-end":"flex-start",
              marginBottom:18,alignItems:"flex-start",gap:10,
              animation:"msgIn 0.25s ease-out"}}>
              {msg.role==="assistant" && (
                <div style={{width:28,height:28,borderRadius:9,flexShrink:0,
                  background:"white",border:"1.5px solid rgba(0,102,255,0.2)",
                  display:"flex",alignItems:"center",justifyContent:"center",
                  marginTop:3,boxShadow:"0 2px 8px rgba(0,102,255,0.1)"}}>
                  <ClauStorMark size={16}/>
                </div>
              )}
              <div style={{maxWidth:"88%",minWidth:0}}>
                <div style={{
                  padding:msg.role==="user"?"10px 16px":"14px 18px",
                  borderRadius:msg.role==="user"?"16px 16px 4px 16px":"4px 16px 16px 16px",
                  background:msg.role==="user"
                    ? "linear-gradient(135deg,#0066FF,#0052CC)"
                    : msg.error
                      ? "#FEF2F2"
                      : "rgba(255,255,255,0.85)",
                  backdropFilter:msg.role==="assistant"?"blur(12px)":"none",
                  color:msg.role==="user"?"white":msg.error?C.error:C.body,
                  border:msg.role==="assistant"
                    ? `1px solid ${msg.error?"#EF444330":"rgba(0,0,0,0.06)"}`
                    : "none",
                  fontSize:13,lineHeight:1.7,
                  boxShadow:msg.role==="user"
                    ? "0 4px 16px rgba(0,102,255,0.25)"
                    : msg.error
                      ? "none"
                      : "0 2px 8px rgba(0,0,0,0.06)"}}>
                  {msg.isStreaming ? (
                    msg.content
                      ? <span>{msg.content}<span style={{display:"inline-block",width:6,height:14,background:C.primary,marginLeft:2,verticalAlign:"text-bottom",borderRadius:2,animation:"blink 0.8s infinite"}}/></span>
                      : <TypingDots/>
                  ) : msg.role==="assistant" && !msg.error ? (
                    <RichText text={msg.content} citations={msg.citations}/>
                  ) : (
                    <span style={{whiteSpace:"pre-wrap"}}>{msg.content}</span>
                  )}
                </div>

                {msg.db_sourced && (
                  <div style={{fontSize:10,color:"#16A34A",marginTop:4,display:"flex",alignItems:"center",gap:4}}>
                    <span>🗄️</span><span style={{fontWeight:600}}>Live Database</span>
                  </div>
                )}

                {msg.role==="assistant" && !msg.isStreaming && !msg.error && !sel && idx===messages.length-1 && (
                  <div style={{fontSize:11,color:C.muted,marginTop:6,padding:"5px 10px",
                    background:"rgba(255,255,255,0.6)",backdropFilter:"blur(8px)",
                    borderRadius:6,border:`1px solid ${C.border}`}}>
                    💡 Select a contract above for focused follow-up questions
                  </div>
                )}

                {msg.role==="assistant" && !msg.isStreaming && !msg.error && (
                  <div style={{marginTop:8}}>
                    <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:10,flexWrap:"wrap"}}>
                      {msg.groundedness!==undefined && !msg.db_sourced && msg.groundedness>0 && (
                        <span style={{fontSize:10,fontWeight:700,padding:"2px 8px",borderRadius:20,
                          background:msg.groundedness>=0.9?"rgba(34,197,94,0.1)":"rgba(245,158,11,0.1)",
                          color:msg.groundedness>=0.9?C.success:C.warning,
                          border:`1px solid ${msg.groundedness>=0.9?C.success:C.warning}30`,
                          backdropFilter:"blur(4px)",
                          display:"inline-flex",alignItems:"center",gap:4}}>
                          <CheckCircle size={9}/> Verified {Math.round(msg.groundedness*100)}%
                        </span>
                      )}
                      {msg.tokens && <span style={{fontSize:10,color:C.muted}}>{msg.tokens.toLocaleString()} tokens</span>}
                      <div style={{marginLeft:"auto",display:"flex",gap:5}}>
                        <button onClick={()=>{navigator.clipboard.writeText(msg.content);setCopied(idx);setTimeout(()=>setCopied(null),2000);}}
                          style={{display:"flex",alignItems:"center",gap:3,padding:"4px 9px",
                            border:`1px solid ${C.border}`,borderRadius:20,
                            background:"rgba(255,255,255,0.7)",backdropFilter:"blur(8px)",
                            cursor:"pointer",fontSize:11,color:C.muted,transition:"all 0.15s"}}
                          onMouseEnter={e=>(e.currentTarget as HTMLElement).style.borderColor=C.primary}
                          onMouseLeave={e=>(e.currentTarget as HTMLElement).style.borderColor=C.border}>
                          {copied===idx?<><Check size={9}/>Copied</>:<><Copy size={9}/>Copy</>}
                        </button>
                        <button onClick={()=>{const prev=messages[idx-1];if(prev)send(prev.content);}}
                          style={{display:"flex",alignItems:"center",gap:3,padding:"4px 9px",
                            border:`1px solid ${C.border}`,borderRadius:20,
                            background:"rgba(255,255,255,0.7)",backdropFilter:"blur(8px)",
                            cursor:"pointer",fontSize:11,color:C.muted,transition:"all 0.15s"}}
                          onMouseEnter={e=>(e.currentTarget as HTMLElement).style.borderColor=C.primary}
                          onMouseLeave={e=>(e.currentTarget as HTMLElement).style.borderColor=C.border}>
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
                              style={{padding:"5px 12px",
                                border:"1px solid rgba(0,102,255,0.2)",borderRadius:20,
                                background:"rgba(0,102,255,0.06)",backdropFilter:"blur(8px)",
                                color:C.primary,fontSize:11,fontWeight:600,cursor:"pointer",transition:"all 0.15s"}}
                              onMouseEnter={e=>{(e.currentTarget as HTMLElement).style.background="rgba(0,102,255,0.15)";(e.currentTarget as HTMLElement).style.borderColor=C.primary;}}
                              onMouseLeave={e=>{(e.currentTarget as HTMLElement).style.background="rgba(0,102,255,0.06)";(e.currentTarget as HTMLElement).style.borderColor="rgba(0,102,255,0.2)";}}>
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
      <div style={{padding:"10px 20px 14px",background:"rgba(255,255,255,0.8)",
        backdropFilter:"blur(12px)",borderTop:`1px solid ${C.border}`,flexShrink:0}}>
        <div style={{maxWidth:800,margin:"0 auto",display:"flex",gap:8,alignItems:"flex-end"}}>
          <div style={{flex:1,border:`1.5px solid ${loading?C.primary:C.border}`,borderRadius:14,
            background:"rgba(255,255,255,0.8)",backdropFilter:"blur(8px)",
            overflow:"hidden",transition:"all 0.15s",
            boxShadow:loading?`0 0 0 3px rgba(0,102,255,0.1)`:"0 2px 8px rgba(0,0,0,0.04)"}}>
            <textarea
              value={input} onChange={e=>setInput(e.target.value)}
              onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send(input);}}}
              placeholder={sel ? `Ask about ${selName}...` : messages.length>1?"💡 Select a contract above for focused follow-ups...":"Ask anything about your contracts..."}
              rows={1} disabled={loading}
              style={{width:"100%",padding:"10px 14px",border:"none",fontSize:13,color:C.heading,
                background:"transparent",resize:"none",outline:"none",fontFamily:"inherit",
                lineHeight:1.5,maxHeight:120,overflowY:"auto",boxSizing:"border-box"}}
              onInput={e=>{const t=e.currentTarget;t.style.height="auto";t.style.height=Math.min(t.scrollHeight,120)+"px";}}
            />
          </div>
          <button onClick={()=>loading?abortRef.current?.abort():send(input)}
            style={{width:40,height:40,borderRadius:12,border:"none",
              background:loading
                ? "rgba(239,68,68,0.1)"
                : input.trim()
                  ? "linear-gradient(135deg,#0066FF,#0052CC)"
                  : "rgba(226,232,240,0.8)",
              backdropFilter:"blur(8px)",
              color:loading?C.error:input.trim()?"white":C.muted,
              cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",
              flexShrink:0,transition:"all 0.2s",
              boxShadow:input.trim()&&!loading?"0 4px 12px rgba(0,102,255,0.3)":"none"}}>
            {loading?<span style={{fontSize:13,fontWeight:700}}>✕</span>:<Send size={15}/>}
          </button>
        </div>
        <p style={{fontSize:10,color:C.muted,textAlign:"center",marginTop:5}}>
          AI-powered · Citations verified · Not legal advice
        </p>
      </div>

      <style>{`
        @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
        @keyframes typingDot{0%,100%{opacity:0.4;transform:translateY(0)}50%{opacity:1;transform:translateY(-3px)}}
        @keyframes msgIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
      `}</style>
    </div>
  );
}

export default function CopilotPage() {
  return (
    <Suspense fallback={<div style={{display:"flex",alignItems:"center",justifyContent:"center",minHeight:"100vh"}}>Loading...</div>}>
      <CopilotPageInner />
    </Suspense>
  );
}
