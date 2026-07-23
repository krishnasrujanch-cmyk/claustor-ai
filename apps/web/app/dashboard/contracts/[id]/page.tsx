"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { contracts as contractsAPI, chat as chatAPI, Contract, Clause } from "@/lib/api";

const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  error:"#EF4444", warning:"#F59E0B", success:"#22C55E",
};

function RiskBadge({ level }: { level: string }) {
  const m: Record<string,{bg:string;text:string}> = {
    high:{bg:"#FEF2F2",text:"#DC2626"},
    medium:{bg:"#FFFBEB",text:"#D97706"},
    low:{bg:"#F0FDF4",text:"#16A34A"},
  };
  const c = m[level] || {bg:"#F3F4F6",text:"#6B7280"};
  return (
    <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,background:c.bg,color:c.text,textTransform:"uppercase"}}>
      {level}
    </span>
  );
}

type Tab = "overview" | "clauses" | "chat";

export default function ContractDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [contract, setContract] = useState<(Contract & { clauses: Clause[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");

  // Chat state
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<Array<{role:string;content:string;citations?:any[]}>>([]);
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    contractsAPI.get(id)
      .then(setContract)
      .catch(() => router.push("/dashboard/contracts"))
      .finally(() => setLoading(false));
  }, [id]);

  const sendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;

    const query = chatInput.trim();
    setChatMessages(prev => [...prev, { role:"user", content:query }]);
    setChatInput("");
    setChatLoading(true);

    try {
      const r = await chatAPI.send(query, id);
      setChatMessages(prev => [...prev, { role:"assistant", content:r.answer, citations:r.citations }]);
    } catch {
      setChatMessages(prev => [...prev, { role:"assistant", content:"Sorry, could not process that query." }]);
    } finally {
      setChatLoading(false);
    }
  };

  if (loading) return (
    <div style={{height:"100%",display:"flex",alignItems:"center",justifyContent:"center"}}>
      <p style={{color:C.muted}}>Loading contract...</p>
    </div>
  );

  if (!contract) return null;

  const tabs: {id:Tab;label:string}[] = [
    {id:"overview", label:"Overview"},
    {id:"clauses",  label:`Clauses (${contract.clauses?.length || 0})`},
    {id:"chat",     label:"AI Copilot"},
  ];

  return (
    <div style={{padding:"32px 36px", maxWidth:1100}}>
      {/* Breadcrumb */}
      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:20,fontSize:13,color:C.muted}}>
        <Link href="/dashboard/contracts" style={{color:C.muted,textDecoration:"none"}}>Contracts</Link>
        <span>›</span>
        <span style={{color:C.body}}>{contract.title}</span>
      </div>

      {/* Header */}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:24}}>
        <div>
          <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:6}}>{contract.title}</h1>
          <div style={{display:"flex",alignItems:"center",gap:12,flexWrap:"wrap"}}>
            {contract.contract_type && (
              <span style={{fontSize:13,color:C.muted,background:C.bg,padding:"2px 10px",borderRadius:20,border:`1px solid ${C.border}`}}>
                {contract.contract_type}
              </span>
            )}
            {contract.risk_level && <RiskBadge level={contract.risk_level} />}
            <span style={{fontSize:13,color:C.muted}}>v{contract.version}</span>
          </div>
        </div>

        {/* Risk score circle */}
        {contract.risk_score !== null && (
          <div style={{textAlign:"center"}}>
            <div style={{
              width:64, height:64, borderRadius:"50%",
              background: contract.risk_score >= 67 ? "#FEF2F2" : contract.risk_score >= 34 ? "#FFFBEB" : "#F0FDF4",
              border: `3px solid ${contract.risk_score >= 67 ? C.error : contract.risk_score >= 34 ? C.warning : C.success}`,
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize:18, fontWeight:800,
              color: contract.risk_score >= 67 ? C.error : contract.risk_score >= 34 ? C.warning : C.success,
            }}>
              {Math.round(contract.risk_score)}
            </div>
            <div style={{fontSize:11,color:C.muted,marginTop:4}}>Risk score</div>
          </div>
        )}
      </div>

      {/* Key info cards */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:12,marginBottom:24}}>
        {[
          {label:"Counterparty", value:contract.counterparty},
          {label:"Contract value", value:contract.contract_value ? `${contract.contract_currency||"USD"} ${(contract.contract_value/1000000).toFixed(2)}M` : null},
          {label:"Effective date", value:contract.effective_date ? new Date(contract.effective_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}) : null},
          {label:"Expiry date", value:contract.expiry_date ? new Date(contract.expiry_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}) : null},
          {label:"Governing law", value:contract.governing_law},
          {label:"Auto renewal", value:contract.auto_renewal === null ? null : contract.auto_renewal ? `Yes (${contract.renewal_notice_days || "?"}d notice)` : "No"},
        ].filter(i=>i.value).map(item=>(
          <div key={item.label} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:10,padding:"12px 16px"}}>
            <div style={{fontSize:11,color:C.muted,marginBottom:4,textTransform:"uppercase",letterSpacing:"0.05em"}}>{item.label}</div>
            <div style={{fontSize:14,fontWeight:600,color:C.heading}}>{item.value}</div>
          </div>
        ))}
      </div>

      {/* Summary */}
      {contract.summary && (
        <div style={{background:C.primaryLight,border:`1px solid ${C.primary}30`,borderRadius:12,padding:"16px 20px",marginBottom:24}}>
          <div style={{fontSize:12,fontWeight:700,color:C.primary,marginBottom:6,textTransform:"uppercase",letterSpacing:"0.05em"}}>AI Summary</div>
          <p style={{fontSize:14,color:C.body,lineHeight:1.6,margin:0}}>{contract.summary}</p>
        </div>
      )}

      {/* Tabs */}
      <div style={{display:"flex",gap:4,marginBottom:20,borderBottom:`1px solid ${C.border}`,paddingBottom:0}}>
        {tabs.map(t=>(
          <button key={t.id} onClick={()=>setTab(t.id)}
            style={{
              padding:"10px 20px", border:"none", background:"none", cursor:"pointer",
              fontSize:14, fontWeight:tab===t.id?700:400,
              color:tab===t.id?C.primary:C.muted,
              borderBottom:tab===t.id?`2px solid ${C.primary}`:"2px solid transparent",
              marginBottom:-1,
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24}}>
          <h3 style={{fontSize:15,fontWeight:700,color:C.heading,marginBottom:12}}>Contract details</h3>
          {[
            {label:"Original filename", value:contract.original_filename},
            {label:"Language", value:contract.language},
            {label:"Total clauses", value:String(contract.clause_count)},
            {label:"Uploaded", value:new Date(contract.created_at).toLocaleString("en-IN")},
            {label:"Last updated", value:new Date(contract.updated_at).toLocaleString("en-IN")},
          ].map(row=>(
            <div key={row.label} style={{display:"flex",justifyContent:"space-between",padding:"10px 0",borderBottom:`1px solid ${C.border}`,fontSize:14}}>
              <span style={{color:C.muted}}>{row.label}</span>
              <span style={{fontWeight:600,color:C.body}}>{row.value||"—"}</span>
            </div>
          ))}
        </div>
      )}

      {tab === "clauses" && (
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          {contract.clauses?.length === 0 ? (
            <div style={{textAlign:"center",padding:60,color:C.muted}}>No clauses extracted yet</div>
          ) : contract.clauses?.map(clause=>(
            <div key={clause.id} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:20}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:10}}>
                <div>
                  <span style={{fontSize:11,fontWeight:700,color:C.primary,textTransform:"uppercase",letterSpacing:"0.05em"}}>{clause.clause_type}</span>
                  {clause.section_reference && <span style={{fontSize:11,color:C.muted,marginLeft:8}}>{clause.section_reference}</span>}
                  <h3 style={{fontSize:15,fontWeight:700,color:C.heading,marginTop:4,marginBottom:0}}>{clause.title}</h3>
                </div>
                <RiskBadge level={clause.risk_level} />
              </div>
              {clause.summary && <p style={{fontSize:14,color:C.body,lineHeight:1.6,margin:0}}>{clause.summary}</p>}
              {clause.risk_reason && (
                <div style={{marginTop:10,padding:"8px 12px",background:C.bg,borderRadius:8,fontSize:13,color:C.muted}}>
                  ⚠️ {clause.risk_reason}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "chat" && (
        <div style={{display:"flex",flexDirection:"column",gap:0,height:500,background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden"}}>
          {/* Messages */}
          <div style={{flex:1,overflowY:"auto",padding:20,display:"flex",flexDirection:"column",gap:16}}>
            {chatMessages.length === 0 && (
              <div style={{textAlign:"center",paddingTop:40,color:C.muted}}>
                <div style={{fontSize:32,marginBottom:12}}>🤖</div>
                <p style={{fontSize:14}}>Ask anything about this contract</p>
                <div style={{display:"flex",flexWrap:"wrap",gap:8,justifyContent:"center",marginTop:16}}>
                  {["What is the liability cap?","What are the payment terms?","When does this contract expire?","Is there auto-renewal?"].map(q=>(
                    <button key={q} onClick={()=>{setChatInput(q);}} style={{padding:"6px 12px",border:`1px solid ${C.border}`,borderRadius:20,background:C.bg,color:C.body,fontSize:12,cursor:"pointer"}}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {chatMessages.map((msg,i)=>(
              <div key={i} style={{display:"flex",justifyContent:msg.role==="user"?"flex-end":"flex-start",gap:10}}>
                <div style={{
                  maxWidth:"75%", padding:"10px 14px", borderRadius:12,
                  background:msg.role==="user"?C.primary:C.bg,
                  color:msg.role==="user"?"white":C.body,
                  fontSize:14, lineHeight:1.6,
                }}>
                  {msg.content}
                  {msg.citations && msg.citations.length > 0 && (
                    <div style={{marginTop:8,display:"flex",flexWrap:"wrap",gap:4}}>
                      {msg.citations.slice(0,3).map((c:any)=>(
                        <span key={c.citation_number} style={{fontSize:10,padding:"2px 6px",borderRadius:10,background:`${C.primary}20`,color:C.primary,fontWeight:600}}>
                          [{c.citation_number}] {c.clause_type||c.source}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div style={{display:"flex",gap:4,paddingLeft:8}}>
                {[0,1,2].map(i=><div key={i} style={{width:8,height:8,borderRadius:"50%",background:C.muted,animation:`bounce 1s ease-in-out ${i*0.15}s infinite`}}/>)}
              </div>
            )}
          </div>

          {/* Input */}
          <form onSubmit={sendChat} style={{display:"flex",gap:10,padding:"12px 16px",borderTop:`1px solid ${C.border}`}}>
            <input value={chatInput} onChange={e=>setChatInput(e.target.value)}
              placeholder="Ask about this contract..." disabled={chatLoading}
              style={{flex:1,padding:"10px 14px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:14,outline:"none"}}
              onFocus={e=>e.target.style.borderColor=C.primary}
              onBlur={e=>e.target.style.borderColor=C.border}
            />
            <button type="submit" disabled={chatLoading||!chatInput.trim()}
              style={{padding:"10px 18px",background:C.primary,color:"white",border:"none",borderRadius:8,fontSize:14,fontWeight:600,cursor:"pointer"}}>
              Ask →
            </button>
          </form>
        </div>
      )}
      <style>{`@keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}`}</style>
    </div>
  );
}
