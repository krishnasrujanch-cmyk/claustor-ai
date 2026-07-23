"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { contracts as contractsAPI, chat as chatAPI, Contract, Clause, getToken } from "@/lib/api";
import { MarkdownText } from "@/components/shared/MarkdownText";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  error:"#EF4444", warning:"#F59E0B", success:"#22C55E",
};

function RiskBadge({ level }: { level:string }) {
  const m: Record<string,any> = {
    high:{bg:"#FEF2F2",text:"#DC2626"},
    medium:{bg:"#FFFBEB",text:"#D97706"},
    low:{bg:"#F0FDF4",text:"#16A34A"},
  };
  const c = m[level]||{bg:"#F3F4F6",text:"#6B7280"};
  return <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,background:c.bg,color:c.text,textTransform:"uppercase"}}>{level}</span>;
}

function RiskHeatmap({ matrix, clauseTypes }: { matrix:any; clauseTypes:string[] }) {
  const getCell = (score:number, count:number) => {
    if (count===0) return {bg:"#F9FAFB",text:"#D1D5DB"};
    if (score>=67) return {bg:"#FEE2E2",text:"#DC2626"};
    if (score>=34) return {bg:"#FEF3C7",text:"#D97706"};
    return {bg:"#DCFCE7",text:"#16A34A"};
  };
  return (
    <div style={{overflowX:"auto"}}>
      <table style={{borderCollapse:"collapse",width:"100%",fontSize:13}}>
        <thead><tr>
          <th style={{padding:"10px 16px",textAlign:"left",color:C.muted,fontWeight:600,minWidth:160,borderBottom:`1px solid ${C.border}`}}>Clause Type</th>
          {["Low Risk","Medium Risk","High Risk"].map(h=>(
            <th key={h} style={{padding:"10px 20px",textAlign:"center",color:C.muted,fontWeight:600,minWidth:120,borderBottom:`1px solid ${C.border}`}}>{h}</th>
          ))}
        </tr></thead>
        <tbody>{clauseTypes.map((ct,i)=>(
          <tr key={ct} style={{borderTop:`1px solid ${C.border}`,background:i%2===0?C.surface:C.bg}}>
            <td style={{padding:"10px 16px",color:C.body,fontWeight:600,textTransform:"capitalize"}}>{ct.replace(/_/g," ")}</td>
            {["low","medium","high"].map(rl=>{
              const cell = matrix[ct]?.[rl]||{count:0,avg_score:0};
              const c2 = getCell(cell.avg_score,cell.count);
              return (
                <td key={rl} style={{padding:"8px 20px",textAlign:"center"}}>
                  {cell.count>0 ? (
                    <div style={{display:"inline-flex",flexDirection:"column",alignItems:"center",background:c2.bg,color:c2.text,borderRadius:10,padding:"6px 14px",minWidth:64}}>
                      <span style={{fontWeight:800,fontSize:16}}>{cell.count}</span>
                      <span style={{fontSize:10,opacity:0.8}}>{cell.avg_score.toFixed(0)} pts</span>
                    </div>
                  ) : <span style={{color:C.border,fontSize:18}}>—</span>}
                </td>
              );
            })}
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

type Tab = "overview"|"clauses"|"analytics"|"chat";

export default function ContractDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [contract, setContract] = useState<(Contract & {clauses:Clause[]})|null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");

  // Assign review modal
  const [showAssign, setShowAssign]     = useState(false);
  const [orgUsers, setOrgUsers]         = useState<any[]>([]);
  const [reviewerId, setReviewerId]     = useState("");
  const [priority, setPriority]         = useState("normal");
  const [reviewNotes, setReviewNotes]   = useState("");
  const [assigning, setAssigning]       = useState(false);
  const [assignMsg, setAssignMsg]       = useState("");

  // Analytics state
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // Chat state
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<Array<{role:string;content:string;citations?:any[]}>>([]);
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    contractsAPI.get(id)
      .then(setContract)
      .catch(()=>router.push("/dashboard/contracts"))
      .finally(()=>setLoading(false));
  }, [id]);

  const loadUsers = async () => {
    const token = getToken();
    const r = await fetch(`${API}/api/v1/users/`, {headers:{Authorization:`Bearer ${token}`}});
    const d = await r.json();
    setOrgUsers(d.users?.filter((u:any) =>
      ["legal_reviewer","contract_manager","dept_admin","super_admin"].includes(u.role)
    ) || []);
  };

  const assignReview = async () => {
    if (!reviewerId) return;
    setAssigning(true); setAssignMsg("");
    const token = getToken();
    try {
      const r = await fetch(`${API}/api/v1/reviews/assign`, {
        method:"POST",
        headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
        body:JSON.stringify({contract_id:id, reviewer_id:reviewerId, priority, notes:reviewNotes||undefined}),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail||"Failed");
      setAssignMsg(`✅ Review assigned to ${d.reviewer}`);
      setTimeout(()=>{ setShowAssign(false); setAssignMsg(""); setReviewerId(""); setReviewNotes(""); }, 2000);
    } catch(e:any) {
      setAssignMsg(`❌ ${e.message}`);
    } finally { setAssigning(false); }
  };

  useEffect(() => {
    if (tab==="analytics" && !analyticsData) {
      setAnalyticsLoading(true);
      const token = getToken();
      const h = {Authorization:`Bearer ${token}`};
      const qs = `?contract_id=${id}`;
      Promise.all([
        fetch(`${API}/api/v1/analytics/overview${qs}`,{headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/analytics/risk-heatmap${qs}`,{headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/analytics/clause-distribution${qs}`,{headers:h}).then(r=>r.json()),
      ]).then(([ov,hm,dist])=>setAnalyticsData({overview:ov,heatmap:hm,distribution:dist}))
      .catch(console.error)
      .finally(()=>setAnalyticsLoading(false));
    }
  }, [tab, id]);

  const sendChat = async (e:React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()||chatLoading) return;
    const query = chatInput.trim();
    setChatMessages(prev=>[...prev,{role:"user",content:query}]);
    setChatInput(""); setChatLoading(true);
    try {
      const r = await chatAPI.send(query,id);
      setChatMessages(prev=>[...prev,{role:"assistant",content:r.answer,citations:r.citations}]);
    } catch {
      setChatMessages(prev=>[...prev,{role:"assistant",content:"Sorry, could not process that."}]);
    } finally { setChatLoading(false); }
  };

  if (loading) return <div style={{height:"100%",display:"flex",alignItems:"center",justifyContent:"center",color:C.muted}}>Loading...</div>;
  if (!contract) return null;

  const tabs:{id:Tab;label:string}[] = [
    {id:"overview",  label:"Overview"},
    {id:"clauses",   label:`Clauses (${contract.clauses?.length||0})`},
    {id:"analytics", label:"Analytics"},
    {id:"chat",      label:"AI Copilot"},
  ];

  return (
    <div style={{padding:"32px 36px",maxWidth:1100}}>
      {/* Breadcrumb */}
      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:20,fontSize:13,color:C.muted}}>
        <Link href="/dashboard/contracts" style={{color:C.muted,textDecoration:"none"}}>Contracts</Link>
        <span>›</span>
        <span style={{color:C.body}}>{contract.title}</span>
      </div>

      {/* Header */}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:24}}>
        <div>
          <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:8}}>{contract.title}</h1>
          <div style={{display:"flex",alignItems:"center",gap:10,flexWrap:"wrap"}}>
            {contract.contract_type && <span style={{fontSize:13,color:C.muted,background:C.bg,padding:"2px 10px",borderRadius:20,border:`1px solid ${C.border}`}}>{contract.contract_type}</span>}
            {contract.risk_level && <RiskBadge level={contract.risk_level}/>}
            <span style={{fontSize:13,color:C.muted}}>v{contract.version}</span>
          </div>
        </div>
        <div style={{display:"flex",flexDirection:"column",gap:10,alignItems:"flex-end"}}>
          <button onClick={()=>{setShowAssign(true);loadUsers();}}
            style={{padding:"8px 18px",background:"#5B4BFF",color:"white",border:"none",borderRadius:8,fontSize:13,fontWeight:600,cursor:"pointer"}}>
            ✅ Assign for review
          </button>
        {contract.risk_score!==null && (
          <div style={{textAlign:"center"}}>
            <div style={{
              width:64,height:64,borderRadius:"50%",
              background:contract.risk_score>=67?"#FEF2F2":contract.risk_score>=34?"#FFFBEB":"#F0FDF4",
              border:`3px solid ${contract.risk_score>=67?C.error:contract.risk_score>=34?C.warning:C.success}`,
              display:"flex",alignItems:"center",justifyContent:"center",
              fontSize:18,fontWeight:800,
              color:contract.risk_score>=67?C.error:contract.risk_score>=34?C.warning:C.success,
            }}>{Math.round(contract.risk_score)}</div>
            <div style={{fontSize:11,color:C.muted,marginTop:4}}>Risk score</div>
          </div>
        )}
        </div>
      </div>

      {/* Key info */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))",gap:12,marginBottom:24}}>
        {[
          {label:"Counterparty",  value:contract.counterparty},
          {label:"Value",         value:contract.contract_value?`${contract.contract_currency||"USD"} ${(contract.contract_value/1000000).toFixed(2)}M`:null},
          {label:"Effective",     value:contract.effective_date?new Date(contract.effective_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):null},
          {label:"Expiry",        value:contract.expiry_date?new Date(contract.expiry_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):null},
          {label:"Governing law", value:contract.governing_law},
          {label:"Auto renewal",  value:contract.auto_renewal===null?null:contract.auto_renewal?`Yes (${contract.renewal_notice_days||"?"}d notice)`:"No"},
        ].filter(i=>i.value).map(item=>(
          <div key={item.label} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:10,padding:"12px 16px"}}>
            <div style={{fontSize:10,color:C.muted,marginBottom:4,textTransform:"uppercase",letterSpacing:"0.05em"}}>{item.label}</div>
            <div style={{fontSize:14,fontWeight:600,color:C.heading}}>{item.value}</div>
          </div>
        ))}
      </div>

      {/* Summary */}
      {contract.summary && (
        <div style={{background:C.primaryLight,border:`1px solid ${C.primary}30`,borderRadius:12,padding:"16px 20px",marginBottom:24}}>
          <div style={{fontSize:11,fontWeight:700,color:C.primary,marginBottom:6,textTransform:"uppercase",letterSpacing:"0.05em"}}>AI Summary</div>
          <p style={{fontSize:14,color:C.body,lineHeight:1.6,margin:0}}>{contract.summary}</p>
        </div>
      )}

      {/* Tabs */}
      <div style={{display:"flex",gap:0,marginBottom:20,borderBottom:`1px solid ${C.border}`}}>
        {tabs.map(t=>(
          <button key={t.id} onClick={()=>setTab(t.id)}
            style={{padding:"10px 22px",border:"none",background:"none",cursor:"pointer",
              fontSize:14,fontWeight:tab===t.id?700:400,
              color:tab===t.id?C.primary:C.muted,
              borderBottom:tab===t.id?`2px solid ${C.primary}`:"2px solid transparent",
              marginBottom:-1}}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab: Overview */}
      {tab==="overview" && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24}}>
          <h3 style={{fontSize:15,fontWeight:700,color:C.heading,marginBottom:12}}>Contract details</h3>
          {[
            {label:"Original filename", value:contract.original_filename},
            {label:"Language",          value:contract.language},
            {label:"Total clauses",     value:String(contract.clause_count)},
            {label:"Uploaded",          value:new Date(contract.created_at).toLocaleString("en-IN")},
            {label:"Last updated",      value:new Date(contract.updated_at).toLocaleString("en-IN")},
          ].map(row=>(
            <div key={row.label} style={{display:"flex",justifyContent:"space-between",padding:"10px 0",borderBottom:`1px solid ${C.border}`,fontSize:14}}>
              <span style={{color:C.muted}}>{row.label}</span>
              <span style={{fontWeight:600,color:C.body}}>{row.value||"—"}</span>
            </div>
          ))}
        </div>
      )}

      {/* Tab: Clauses */}
      {tab==="clauses" && (
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          {contract.clauses?.length===0 ? (
            <div style={{textAlign:"center",padding:60,color:C.muted}}>No clauses extracted yet</div>
          ) : contract.clauses?.map(clause=>(
            <div key={clause.id} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:20}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:10}}>
                <div>
                  <span style={{fontSize:11,fontWeight:700,color:C.primary,textTransform:"uppercase",letterSpacing:"0.05em"}}>{clause.clause_type}</span>
                  {clause.section_reference && <span style={{fontSize:11,color:C.muted,marginLeft:8}}>{clause.section_reference}</span>}
                  <h3 style={{fontSize:15,fontWeight:700,color:C.heading,marginTop:4,marginBottom:0}}>{clause.title}</h3>
                </div>
                <RiskBadge level={clause.risk_level}/>
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

      {/* Tab: Analytics */}
      {tab==="analytics" && (
        analyticsLoading ? (
          <div style={{textAlign:"center",padding:60,color:C.muted}}>Loading analytics...</div>
        ) : analyticsData ? (
          <div style={{display:"flex",flexDirection:"column",gap:20}}>
            {/* Stats row */}
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))",gap:16}}>
              {[
                {label:"Risk score",    value:contract.risk_score!==null?Math.round(contract.risk_score):"-", color:contract.risk_score&&contract.risk_score>=67?C.error:contract.risk_score&&contract.risk_score>=34?C.warning:C.success},
                {label:"Total clauses", value:analyticsData.overview.clauses.total, color:"#6366F1"},
                {label:"Avg clause risk",value:analyticsData.overview.clauses.avg_risk, color:C.primary},
                {label:"Contract value", value:contract.contract_value?`$${(contract.contract_value/1000000).toFixed(2)}M`:"—", color:C.primary},
              ].map(s=>(
                <div key={s.label} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:"20px 24px"}}>
                  <div style={{fontSize:12,color:C.muted,marginBottom:8,textTransform:"uppercase",letterSpacing:"0.05em"}}>{s.label}</div>
                  <div style={{fontSize:28,fontWeight:800,color:s.color}}>{s.value}</div>
                </div>
              ))}
            </div>

            {/* Clause distribution */}
            {analyticsData.distribution?.distribution?.length>0 && (
              <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24}}>
                <h2 style={{fontSize:15,fontWeight:700,color:C.heading,marginBottom:20}}>
                  Clause breakdown <span style={{fontSize:12,color:C.muted,fontWeight:400}}>({analyticsData.distribution.total_clauses} clauses)</span>
                </h2>
                <div style={{display:"flex",flexDirection:"column",gap:10}}>
                  {analyticsData.distribution.distribution.map((item:any)=>(
                    <div key={item.clause_type}>
                      <div style={{display:"flex",justifyContent:"space-between",fontSize:13,marginBottom:4}}>
                        <span style={{color:C.body,fontWeight:500,textTransform:"capitalize"}}>{item.clause_type.replace(/_/g," ")}</span>
                        <div style={{display:"flex",gap:12,alignItems:"center"}}>
                          <span style={{fontSize:11,padding:"1px 6px",borderRadius:10,
                            background:item.avg_risk>=67?"#FEF2F2":item.avg_risk>=34?"#FFFBEB":"#F0FDF4",
                            color:item.avg_risk>=67?C.error:item.avg_risk>=34?C.warning:C.success,
                            fontWeight:600}}>
                            risk {item.avg_risk}
                          </span>
                          <span style={{color:C.muted,fontSize:12}}>{item.count} ({item.pct}%)</span>
                        </div>
                      </div>
                      <div style={{height:8,background:C.border,borderRadius:4,overflow:"hidden"}}>
                        <div style={{height:"100%",width:`${item.pct}%`,
                          background:item.avg_risk>=67?C.error:item.avg_risk>=34?C.warning:C.primary,
                          borderRadius:4}}/>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Risk Heatmap */}
            {analyticsData.heatmap?.clause_types?.length>0 && (
              <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24}}>
                <h2 style={{fontSize:15,fontWeight:700,color:C.heading,marginBottom:4}}>Risk Heatmap</h2>
                <p style={{fontSize:13,color:C.muted,marginBottom:20}}>Clause type vs risk level for this contract</p>
                <RiskHeatmap matrix={analyticsData.heatmap.matrix} clauseTypes={analyticsData.heatmap.clause_types}/>
              </div>
            )}
          </div>
        ) : null
      )}

      {/* Tab: Chat */}
      {tab==="chat" && (
        <div style={{display:"flex",flexDirection:"column",height:520,background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden"}}>
          <div style={{flex:1,overflowY:"auto",padding:20,display:"flex",flexDirection:"column",gap:16}}>
            {chatMessages.length===0 && (
              <div style={{textAlign:"center",paddingTop:40,color:C.muted}}>
                <div style={{fontSize:32,marginBottom:12}}>🤖</div>
                <p style={{fontSize:14,marginBottom:20}}>Ask anything about this contract</p>
                <div style={{display:"flex",flexWrap:"wrap",gap:8,justifyContent:"center"}}>
                  {["What is the liability cap?","What are the payment terms?","When does this expire?","Is there auto-renewal?"].map(q=>(
                    <button key={q} onClick={()=>setChatInput(q)}
                      style={{padding:"6px 12px",border:`1px solid ${C.border}`,borderRadius:20,background:C.bg,color:C.body,fontSize:12,cursor:"pointer"}}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {chatMessages.map((msg,i)=>(
              <div key={i} style={{display:"flex",justifyContent:msg.role==="user"?"flex-end":"flex-start",gap:10}}>
                <div style={{maxWidth:"75%",padding:"10px 14px",borderRadius:12,
                  background:msg.role==="user"?C.primary:C.bg,
                  color:msg.role==="user"?"white":C.body,
                  border:msg.role==="assistant"?`1px solid ${C.border}`:"none",
                  fontSize:14,lineHeight:1.6}}>
                  {msg.role==="assistant" ? <MarkdownText content={msg.content} color={C.body}/> : msg.content}
                  {msg.citations && msg.citations.length>0 && (
                    <div style={{marginTop:8,display:"flex",flexWrap:"wrap",gap:4}}>
                      {msg.citations.slice(0,3).map((cite:any)=>(
                        <span key={cite.citation_number} style={{fontSize:10,padding:"2px 6px",borderRadius:10,background:`${C.primary}20`,color:C.primary,fontWeight:600}}>
                          [{cite.citation_number}] {cite.clause_type||cite.source}
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
          <form onSubmit={sendChat} style={{display:"flex",gap:10,padding:"12px 16px",borderTop:`1px solid ${C.border}`}}>
            <input value={chatInput} onChange={e=>setChatInput(e.target.value)}
              placeholder="Ask about this contract..." disabled={chatLoading}
              style={{flex:1,padding:"10px 14px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:14,outline:"none"}}
              onFocus={e=>e.target.style.borderColor=C.primary}
              onBlur={e=>e.target.style.borderColor=C.border}/>
            <button type="submit" disabled={chatLoading||!chatInput.trim()}
              style={{padding:"10px 18px",background:C.primary,color:"white",border:"none",borderRadius:8,fontSize:14,fontWeight:600,cursor:"pointer"}}>
              Ask →
            </button>
          </form>
        </div>
      )}
      <style>{`@keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}`}</style>

      {/* Assign Review Modal */}
      {showAssign && (
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:100}}>
          <div style={{background:C.surface,borderRadius:16,padding:32,width:480,boxShadow:"0 20px 60px rgba(0,0,0,0.2)"}}>
            <h2 style={{fontSize:18,fontWeight:700,color:C.heading,marginBottom:4}}>Assign for Review</h2>
            <p style={{fontSize:13,color:C.muted,marginBottom:24}}>{contract?.title}</p>

            {assignMsg && (
              <div style={{padding:"10px 14px",borderRadius:8,marginBottom:16,
                background:assignMsg.startsWith("✅")?"#F0FDF4":"#FEF2F2",
                color:assignMsg.startsWith("✅")?C.success:C.error,fontSize:13}}>
                {assignMsg}
              </div>
            )}

            <div style={{display:"flex",flexDirection:"column",gap:14}}>
              <div>
                <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Reviewer</label>
                <select value={reviewerId} onChange={e=>setReviewerId(e.target.value)}
                  style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13,color:C.body}}>
                  <option value="">Select reviewer...</option>
                  {orgUsers.map(u=>(
                    <option key={u.id} value={u.id}>{u.full_name||u.email} ({u.role})</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Priority</label>
                <div style={{display:"flex",gap:8}}>
                  {["low","normal","high","urgent"].map(p=>(
                    <button key={p} onClick={()=>setPriority(p)}
                      style={{flex:1,padding:"8px",border:`2px solid ${priority===p?"#5B4BFF":C.border}`,
                        borderRadius:8,background:priority===p?"#EEF0FF":"none",
                        color:priority===p?"#5B4BFF":C.muted,fontSize:12,fontWeight:600,cursor:"pointer",textTransform:"capitalize"}}>
                      {p}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Notes (optional)</label>
                <textarea value={reviewNotes} onChange={e=>setReviewNotes(e.target.value)}
                  placeholder="Instructions for reviewer..." rows={3}
                  style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13,resize:"vertical",outline:"none"}}/>
              </div>
            </div>

            <div style={{display:"flex",gap:10,justifyContent:"flex-end",marginTop:20}}>
              <button onClick={()=>{setShowAssign(false);setAssignMsg("");}}
                style={{padding:"10px 20px",border:`1px solid ${C.border}`,borderRadius:8,background:"none",fontSize:14,cursor:"pointer"}}>
                Cancel
              </button>
              <button onClick={assignReview} disabled={!reviewerId||assigning}
                style={{padding:"10px 20px",border:"none",borderRadius:8,
                  background:!reviewerId||assigning?"#D1D5DB":"#5B4BFF",
                  color:"white",fontSize:14,fontWeight:600,cursor:!reviewerId?"not-allowed":"pointer"}}>
                {assigning?"Assigning...":"Assign review"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
