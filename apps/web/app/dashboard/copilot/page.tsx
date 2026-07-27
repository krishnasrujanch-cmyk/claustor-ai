"use client";
const API = "http://localhost:8000";

import { useEffect, useRef, useState, useCallback } from "react";
import { chat as chatAPI, contracts as contractsAPI, Contract, getToken } from "@/lib/api";
import { MarkdownText } from "@/components/shared/MarkdownText";
import { C } from "@/lib/design-tokens";

interface Message {
  role: "user"|"assistant";
  content: string;
  citations?: Array<{citation_number:number;clause_type:string;source:string;text_preview:string;rrf_score:number}>;
  isLoading?: boolean;
  followUps?: string[];
  timestamp?: Date;
}

// ── Categorized prompt suggestions ────────────────────────────────────────────
const PROMPT_CATEGORIES = [
  {
    label: "Risk & Liability",
    icon: "🛡️",
    color: "#EF4444",
    prompts: [
      {icon:"🛡️", text:"What is the liability cap?"},
      {icon:"💰", text:"Is indemnification capped or unlimited?"},
      {icon:"⚠️", text:"What are the high-risk clauses?"},
    ],
  },
  {
    label: "Financial",
    icon: "💳",
    color: "#F59E0B",
    prompts: [
      {icon:"💳", text:"What are the payment terms?"},
      {icon:"📈", text:"Are there any price escalation clauses?"},
      {icon:"🔄", text:"Is there an auto-renewal clause?"},
    ],
  },
  {
    label: "Legal & Governance",
    icon: "⚖️",
    color: "#0066FF",
    prompts: [
      {icon:"⚖️", text:"What is the governing law?"},
      {icon:"👥", text:"Who are the parties to this contract?"},
      {icon:"🚪", text:"What are the termination conditions?"},
    ],
  },
  {
    label: "IP & Data",
    icon: "🔐",
    color: "#22C55E",
    prompts: [
      {icon:"🔐", text:"Who owns the intellectual property?"},
      {icon:"🗄️", text:"What are the data protection obligations?"},
      {icon:"🤐", text:"What is the confidentiality period?"},
    ],
  },
];

// ── Animated AI Orb ───────────────────────────────────────────────────────────
function AIOrb({ size=64 }: { size?: number }) {
  return (
    <div style={{
      width:size, height:size, borderRadius:"50%", flexShrink:0,
      background:`conic-gradient(from 0deg, ${C.primary}, ${C.accent}, #A855F7, ${C.primary})`,
      display:"flex", alignItems:"center", justifyContent:"center",
      boxShadow:`0 0 ${size/3}px ${C.primary}50`,
      animation:"orb-spin 4s linear infinite",
      position:"relative",
    }}>
      <div style={{
        width:size*0.7, height:size*0.7, borderRadius:"50%",
        background:C.surface, display:"flex", alignItems:"center", justifyContent:"center",
        fontSize:size*0.3, fontWeight:800, color:C.primary,
      }}>✦</div>
    </div>
  );
}

// ── Scope selector pill ───────────────────────────────────────────────────────
function ScopeSelector({ contracts, selected, onChange }: {
  contracts: Contract[]; selected: string; onChange: (v:string)=>void;
}) {
  return (
    <div style={{display:"flex",alignItems:"center",gap:6,
      padding:"6px 12px",border:`1.5px solid ${C.primary}40`,
      borderRadius:20,background:C.primaryLight,cursor:"pointer",
      flexShrink:0}}>
      <span style={{fontSize:12,color:C.primary}}>📄</span>
      <select value={selected} onChange={e=>onChange(e.target.value)}
        style={{border:"none",background:"transparent",color:C.primary,
          fontSize:12,fontWeight:600,cursor:"pointer",outline:"none",
          maxWidth:160}}>
        <option value="">All Contracts</option>
        {contracts.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}
      </select>
    </div>
  );
}

// ── Citation card ─────────────────────────────────────────────────────────────
function CitationCard({ cite, onClick }: { cite:any; onClick?:()=>void }) {
  return (
    <div onClick={onClick}
      style={{display:"flex",gap:8,padding:"6px 10px",
        background:C.bg,border:`1px solid ${C.border}`,
        borderRadius:8,fontSize:12,cursor:onClick?"pointer":"default",
        transition:"all 0.15s"}}
      onMouseEnter={e=>onClick&&(e.currentTarget.style.borderColor=C.primary)}
      onMouseLeave={e=>onClick&&(e.currentTarget.style.borderColor=C.border)}>
      <span style={{width:18,height:18,borderRadius:"50%",background:C.primaryLight,
        color:C.primary,display:"flex",alignItems:"center",justifyContent:"center",
        fontWeight:700,flexShrink:0,fontSize:10}}>
        {cite.citation_number}
      </span>
      <div style={{minWidth:0}}>
        <span style={{fontSize:10,fontWeight:700,color:C.primary,
          textTransform:"uppercase",letterSpacing:"0.05em"}}>
          {cite.clause_type||cite.source}
        </span>
        <p style={{color:C.muted,margin:0,lineHeight:1.4,marginTop:2,
          overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:300}}>
          "{cite.text_preview?.slice(0,80)}..."
        </p>
      </div>
    </div>
  );
}

export default function CopilotPage() {
  const [contracts, setContracts]     = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract]   = useState<string>("");
  const [selectedReviewStatus, setSelectedReviewStatus] = useState<string|null>(null);
  const [selectedReviewNotes, setSelectedReviewNotes]   = useState<string|null>(null);
  const [messages, setMessages]       = useState<Message[]>([]);
  const [input, setInput]             = useState("");
  const [isLoading, setIsLoading]     = useState(false);
  const [activeCategory, setActiveCategory] = useState(0);
  const [copiedIdx, setCopiedIdx]     = useState<number|null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    contractsAPI.list({ status:"analyzed", page_size:50 })
      .then(d => setContracts(d.contracts));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior:"smooth" });
  }, [messages]);

  useEffect(() => {
    if (!selectedContract) { setSelectedReviewStatus(null); return; }
    const token = getToken() || "";
    fetch(`${API}/api/v1/contracts/${selectedContract}`,
      {headers:{Authorization:`Bearer ${token}`}})
    .then(r=>r.json())
    .then(d=>{ setSelectedReviewStatus(d.review_status||null); setSelectedReviewNotes(d.review_notes||null); })
    .catch(console.error);
  }, [selectedContract]);

  const handleContractChange = (val: string) => {
    setSelectedContract(val);
    setMessages([]);
  };

  const copyMessage = useCallback((content: string, idx: number) => {
    navigator.clipboard.writeText(content);
    setCopiedIdx(idx);
    setTimeout(()=>setCopiedIdx(null), 2000);
  }, []);

  const sendMessage = async (query: string) => {
    if (!query.trim() || isLoading) return;
    setMessages(prev => [...prev,
      { role:"user", content:query, timestamp:new Date() },
      { role:"assistant", content:"", isLoading:true },
    ]);
    setInput("");
    setIsLoading(true);
    inputRef.current?.focus();
    try {
      const r = await chatAPI.send(query, selectedContract||undefined);
      
      // Generate follow-up suggestions based on query
      const followUps = generateFollowUps(query, r.answer);

      setMessages(prev => [...prev.slice(0,-1), {
        role:"assistant", content:r.answer, citations:r.citations,
        followUps, timestamp:new Date(),
      }]);
    } catch {
      setMessages(prev => [...prev.slice(0,-1), {
        role:"assistant",
        content:"Sorry, I couldn't process that query. Please try again.",
        timestamp:new Date(),
      }]);
    } finally { setIsLoading(false); }
  };

  const generateFollowUps = (query: string, answer: string): string[] => {
    const q = query.toLowerCase();
    if (q.includes("payment") || q.includes("terms"))
      return ["Are there late payment penalties?","What currency is used?","Is there a payment dispute process?"];
    if (q.includes("terminat"))
      return ["What happens to data after termination?","Is there a wind-down period?","Are payments due on termination?"];
    if (q.includes("liability") || q.includes("indemnif"))
      return ["What are the insurance requirements?","Are consequential damages excluded?","Who indemnifies for IP infringement?"];
    if (q.includes("ip") || q.includes("intellectual"))
      return ["What happens to IP after termination?","Is there a license grant?","Are improvements covered?"];
    if (q.includes("renewal") || q.includes("auto"))
      return ["What is the notice period for non-renewal?","Can pricing change on renewal?","Who initiates renewal?"];
    return ["Can you summarize the key risks?","What clauses are missing?","What is the governing law?"];
  };

  const isEmpty = messages.length === 0;

  return (
    <div style={{height:"100%",display:"flex",flexDirection:"column",
      maxWidth:900,margin:"0 auto",padding:"0 24px"}}>

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div style={{padding:"24px 0 16px",borderBottom:`1px solid ${C.border}`,
        flexShrink:0}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <h1 style={{fontSize:20,fontWeight:800,color:C.heading,marginBottom:2}}>
              AI Copilot
            </h1>
            <p style={{fontSize:13,color:C.muted}}>
              Ask anything about your contracts. Answers cited from actual source documents.
            </p>
          </div>
          {/* Show scope selector in header only when conversation active */}
          {!isEmpty && (
            <ScopeSelector contracts={contracts} selected={selectedContract}
              onChange={handleContractChange}/>
          )}
        </div>
      </div>

      {/* ── Rejection banner ─────────────────────────────────────────────── */}
      {selectedContract && selectedReviewStatus &&
        ["rejected","revision_needed"].includes(selectedReviewStatus) && (
        <div style={{margin:"12px 0",padding:"10px 16px",borderRadius:10,
          background:selectedReviewStatus==="rejected"?"#FEF2F2":"#FFFBEB",
          border:`2px solid ${selectedReviewStatus==="rejected"?"#EF4444":"#F59E0B"}`,
          display:"flex",alignItems:"center",gap:10}}>
          <span style={{fontSize:18}}>
            {selectedReviewStatus==="rejected"?"❌":"🔄"}
          </span>
          <div>
            <span style={{fontSize:13,fontWeight:800,
              color:selectedReviewStatus==="rejected"?"#DC2626":"#D97706"}}>
              {selectedReviewStatus==="rejected"
                ?"CONTRACT REJECTED — Do not execute"
                :"REVISION REQUIRED — Address issues before signing"}
            </span>
            {selectedReviewNotes && (
              <span style={{fontSize:12,color:"#374151",marginLeft:8}}>
                · {selectedReviewNotes}
              </span>
            )}
          </div>
        </div>
      )}

      {/* ── Messages / Empty state ───────────────────────────────────────── */}
      <div style={{flex:1,overflowY:"auto",padding:"24px 0",
        display:"flex",flexDirection:"column",gap:20}}>

        {/* Empty state — search engine style */}
        {isEmpty && (
          <div style={{display:"flex",flexDirection:"column",
            alignItems:"center",paddingTop:40,gap:20}}>

            {/* Animated orb */}
            <AIOrb size={72}/>

            <div style={{textAlign:"center"}}>
              <h2 style={{fontSize:22,fontWeight:800,color:C.heading,marginBottom:6}}>
                Ask your contracts anything
              </h2>
              <p style={{fontSize:14,color:C.muted}}>
                {selectedContract
                  ? "Asking about the selected contract"
                  : "Select a contract or query across your entire portfolio"}
              </p>
            </div>

            {/* Central input with scope selector embedded */}
            <div style={{width:"100%",maxWidth:640}}>
              <div style={{display:"flex",gap:0,border:`2px solid ${C.primary}`,
                borderRadius:14,overflow:"hidden",background:C.surface,
                boxShadow:`0 4px 20px ${C.primary}20`}}>
                <input ref={inputRef} value={input}
                  onChange={e=>setInput(e.target.value)}
                  onKeyDown={e=>e.key==="Enter"&&!e.shiftKey&&sendMessage(input)}
                  placeholder="Ask anything about your contracts..."
                  style={{flex:1,padding:"14px 16px",border:"none",
                    fontSize:14,color:C.body,outline:"none",background:"transparent"}}/>
                <div style={{borderLeft:`1px solid ${C.border}`,display:"flex",
                  alignItems:"center",padding:"0 12px",flexShrink:0}}>
                  <ScopeSelector contracts={contracts} selected={selectedContract}
                    onChange={handleContractChange}/>
                </div>
                <button onClick={()=>sendMessage(input)}
                  disabled={isLoading||!input.trim()}
                  style={{padding:"0 20px",background:input.trim()?C.primary:"#D1D5DB",
                    color:"white",border:"none",fontSize:14,fontWeight:700,
                    cursor:input.trim()?"pointer":"not-allowed",
                    transition:"background 0.2s"}}>
                  Ask →
                </button>
              </div>
            </div>

            {/* Category tabs */}
            <div style={{width:"100%",maxWidth:640}}>
              <div style={{display:"flex",gap:6,marginBottom:12,flexWrap:"wrap"}}>
                {PROMPT_CATEGORIES.map((cat,i)=>(
                  <button key={cat.label} onClick={()=>setActiveCategory(i)}
                    style={{padding:"5px 12px",borderRadius:20,border:"none",
                      cursor:"pointer",fontSize:12,fontWeight:600,transition:"all 0.15s",
                      background:activeCategory===i?cat.color:"#F3F4F6",
                      color:activeCategory===i?"white":"#6B7280"}}>
                    {cat.icon} {cat.label}
                  </button>
                ))}
              </div>

              {/* Prompt pills */}
              <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
                {PROMPT_CATEGORIES[activeCategory].prompts.map(p=>(
                  <button key={p.text} onClick={()=>sendMessage(p.text)}
                    style={{padding:"8px 14px",
                      border:`1.5px solid ${C.border}`,borderRadius:20,
                      background:C.surface,color:C.body,fontSize:13,
                      cursor:"pointer",display:"flex",gap:6,alignItems:"center",
                      transition:"all 0.15s"}}
                    onMouseEnter={e=>{
                      e.currentTarget.style.borderColor=C.primary;
                      e.currentTarget.style.background=C.primaryLight;
                      e.currentTarget.style.color=C.primary;
                    }}
                    onMouseLeave={e=>{
                      e.currentTarget.style.borderColor=C.border;
                      e.currentTarget.style.background=C.surface;
                      e.currentTarget.style.color=C.body;
                    }}>
                    <span>{p.icon}</span>{p.text}
                  </button>
                ))}
              </div>
            </div>

            <p style={{fontSize:11,color:C.muted,marginTop:8}}>
              Answers cited from your contracts. Not legal advice.
            </p>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, i) => (
          <div key={i} style={{display:"flex",
            justifyContent:msg.role==="user"?"flex-end":"flex-start",gap:12}}>
            {msg.role==="assistant" && (
              <div style={{flexShrink:0,marginTop:4}}>
                <AIOrb size={32}/>
              </div>
            )}
            <div style={{maxWidth:"78%"}}>
              <div style={{
                padding:"12px 16px",
                borderRadius:msg.role==="user"?"16px 16px 4px 16px":"16px 16px 16px 4px",
                background:msg.role==="user"?C.primary:C.surface,
                color:msg.role==="user"?"white":C.body,
                border:msg.role==="assistant"?`1px solid ${C.border}`:"none",
                boxShadow:msg.role==="assistant"?"0 1px 3px rgba(0,0,0,0.06)":"none",
              }}>
                {msg.isLoading ? (
                  <div style={{display:"flex",gap:4,padding:"4px 0"}}>
                    {[0,1,2].map(j=>(
                      <div key={j} style={{width:8,height:8,borderRadius:"50%",
                        background:C.muted,
                        animation:`bounce 1s ease-in-out ${j*0.15}s infinite`}}/>
                    ))}
                  </div>
                ) : msg.role==="assistant" ? (
                  <MarkdownText content={msg.content} color={C.body}/>
                ) : (
                  <span style={{fontSize:14}}>{msg.content}</span>
                )}
              </div>

              {/* Action buttons for assistant messages */}
              {msg.role==="assistant" && !msg.isLoading && msg.content && (
                <div style={{display:"flex",gap:8,marginTop:6,alignItems:"center"}}>
                  <button onClick={()=>copyMessage(msg.content,i)}
                    style={{padding:"3px 10px",border:`1px solid ${C.border}`,
                      borderRadius:20,background:C.surface,fontSize:11,
                      color:copiedIdx===i?C.success:C.muted,cursor:"pointer",
                      fontWeight:600}}>
                    {copiedIdx===i?"✅ Copied":"📋 Copy"}
                  </button>
                  {msg.timestamp && (
                    <span style={{fontSize:10,color:C.muted}}>
                      {msg.timestamp.toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"})}
                    </span>
                  )}
                </div>
              )}

              {/* Citations */}
              {msg.citations && msg.citations.length>0 && (
                <div style={{marginTop:8,display:"flex",flexDirection:"column",gap:4}}>
                  {msg.citations.slice(0,3).map(cite=>(
                    <CitationCard key={cite.citation_number} cite={cite}/>
                  ))}
                </div>
              )}

              {/* Follow-up suggestions */}
              {msg.role==="assistant" && !msg.isLoading && msg.followUps && (
                <div style={{marginTop:10}}>
                  <div style={{fontSize:11,color:C.muted,marginBottom:6,fontWeight:600}}>
                    You might also ask:
                  </div>
                  <div style={{display:"flex",flexWrap:"wrap",gap:6}}>
                    {msg.followUps.map(q=>(
                      <button key={q} onClick={()=>sendMessage(q)}
                        style={{padding:"5px 12px",border:`1px solid ${C.primary}30`,
                          borderRadius:20,background:C.primaryLight,
                          color:C.primary,fontSize:12,cursor:"pointer",
                          fontWeight:500,transition:"all 0.15s"}}
                        onMouseEnter={e=>{e.currentTarget.style.background=C.primary;e.currentTarget.style.color="white";}}
                        onMouseLeave={e=>{e.currentTarget.style.background=C.primaryLight;e.currentTarget.style.color=C.primary;}}>
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef}/>
      </div>

      {/* ── Bottom input bar (shown when conversation active) ─────────────── */}
      {!isEmpty && (
        <div style={{padding:"12px 0 20px",borderTop:`1px solid ${C.border}`,flexShrink:0}}>
          <div style={{display:"flex",gap:0,border:`1.5px solid ${C.border}`,
            borderRadius:12,overflow:"hidden",background:C.surface,
            transition:"border-color 0.2s"}}
            onFocusCapture={e=>e.currentTarget.style.borderColor=C.primary}
            onBlurCapture={e=>e.currentTarget.style.borderColor=C.border}>
            <input ref={inputRef} value={input}
              onChange={e=>setInput(e.target.value)}
              onKeyDown={e=>e.key==="Enter"&&!e.shiftKey&&sendMessage(input)}
              placeholder="Ask a follow-up question..."
              disabled={isLoading}
              style={{flex:1,padding:"12px 16px",border:"none",
                fontSize:14,color:C.body,outline:"none",background:"transparent"}}/>
            <div style={{borderLeft:`1px solid ${C.border}`,display:"flex",
              alignItems:"center",padding:"0 10px"}}>
              <ScopeSelector contracts={contracts} selected={selectedContract}
                onChange={handleContractChange}/>
            </div>
            <button onClick={()=>sendMessage(input)}
              disabled={isLoading||!input.trim()}
              style={{padding:"0 20px",background:input.trim()&&!isLoading?C.primary:"#D1D5DB",
                color:"white",border:"none",fontSize:14,fontWeight:700,
                cursor:input.trim()&&!isLoading?"pointer":"not-allowed"}}>
              {isLoading?"...":"Ask →"}
            </button>
          </div>
          <p style={{fontSize:11,color:C.muted,marginTop:8,textAlign:"center"}}>
            Answers cited from your contracts. Not legal advice.
          </p>
        </div>
      )}

      <style>{`
        @keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
        @keyframes orb-spin{from{filter:hue-rotate(0deg)}to{filter:hue-rotate(360deg)}}
      `}</style>
    </div>
  );
}
