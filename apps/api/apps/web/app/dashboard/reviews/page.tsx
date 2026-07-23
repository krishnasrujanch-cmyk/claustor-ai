"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getToken } from "@/lib/api";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  error:"#EF4444", warning:"#F59E0B", success:"#22C55E",
};

const PRIORITY_COLORS: Record<string,{bg:string;text:string}> = {
  urgent:{bg:"#FEF2F2",text:"#DC2626"},
  high:  {bg:"#FFFBEB",text:"#D97706"},
  normal:{bg:"#EEF0FF",text:"#5B4BFF"},
  low:   {bg:"#F0FDF4",text:"#16A34A"},
};

const STATUS_COLORS: Record<string,{bg:string;text:string}> = {
  pending:         {bg:"#FFFBEB",text:"#D97706"},
  in_review:       {bg:"#EEF0FF",text:"#5B4BFF"},
  approved:        {bg:"#F0FDF4",text:"#16A34A"},
  rejected:        {bg:"#FEF2F2",text:"#DC2626"},
  revision_needed: {bg:"#FFF7ED",text:"#C2410C"},
};

export default function ReviewsPage() {
  const [queue, setQueue]     = useState<any[]>([]);
  const [all, setAll]         = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab]         = useState<"my-queue"|"all">("my-queue");
  const [modal, setModal]     = useState<{reviewId:string;title:string}|null>(null);
  const [decision, setDecision]     = useState("");
  const [notes, setNotes]           = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    setLoading(true);
    const token = getToken();
    const h = { Authorization:`Bearer ${token}` };
    try {
      const [qR, aR] = await Promise.all([
        fetch(`${API}/api/v1/reviews/my-queue`, {headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/reviews/`, {headers:h}).then(r=>r.json()),
      ]);
      setQueue(qR.queue||[]); setAll(aR.reviews||[]);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const startReview = async (id: string) => {
    const token = getToken();
    await fetch(`${API}/api/v1/reviews/${id}/start`, {method:"POST",headers:{Authorization:`Bearer ${token}`}});
    load();
  };

  const submitDecision = async () => {
    if (!modal||!decision) return;
    setSubmitting(true);
    const token = getToken();
    try {
      await fetch(`${API}/api/v1/reviews/${modal.reviewId}/decide`, {
        method:"POST",
        headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
        body:JSON.stringify({decision,decision_notes:notes}),
      });
      setModal(null); setDecision(""); setNotes("");
      load();
    } finally { setSubmitting(false); }
  };

  return (
    <div style={{padding:"32px 36px"}}>
      <div style={{marginBottom:28}}>
        <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Review Workflow</h1>
        <p style={{fontSize:14,color:C.muted}}>Manage contract reviews and approvals</p>
      </div>

      {/* Stats */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))",gap:16,marginBottom:28}}>
        {[
          {label:"My queue",   value:queue.length,                                     color:C.primary},
          {label:"Pending",    value:all.filter(r=>r.status==="pending").length,        color:C.warning},
          {label:"In review",  value:all.filter(r=>r.status==="in_review").length,     color:C.primary},
          {label:"Approved",   value:all.filter(r=>r.status==="approved").length,      color:C.success},
          {label:"Rejected",   value:all.filter(r=>r.status==="rejected").length,      color:C.error},
        ].map(s=>(
          <div key={s.label} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:"16px 20px"}}>
            <div style={{fontSize:12,color:C.muted,marginBottom:6}}>{s.label}</div>
            <div style={{fontSize:28,fontWeight:800,color:s.color}}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{display:"flex",borderBottom:`1px solid ${C.border}`,marginBottom:20}}>
        {[{id:"my-queue",label:`My Queue (${queue.length})`},{id:"all",label:`All Reviews (${all.length})`}].map(t=>(
          <button key={t.id} onClick={()=>setTab(t.id as any)}
            style={{padding:"10px 22px",border:"none",background:"none",cursor:"pointer",fontSize:14,
              fontWeight:tab===t.id?700:400,color:tab===t.id?C.primary:C.muted,
              borderBottom:tab===t.id?`2px solid ${C.primary}`:"2px solid transparent",marginBottom:-1}}>
            {t.label}
          </button>
        ))}
      </div>

      {tab==="my-queue" && (
        loading ? <div style={{textAlign:"center",padding:60,color:C.muted}}>Loading...</div>
        : queue.length===0 ? (
          <div style={{textAlign:"center",padding:80,background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
            <div style={{fontSize:48,marginBottom:16}}>✅</div>
            <p style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:8}}>Queue is empty</p>
            <p style={{fontSize:14,color:C.muted}}>No contracts assigned to you for review</p>
          </div>
        ) : (
          <div style={{display:"flex",flexDirection:"column",gap:16}}>
            {queue.map(item=>(
              <div key={item.review_id} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:16}}>
                  <div>
                    <div style={{display:"flex",gap:8,marginBottom:8}}>
                      <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:20,background:PRIORITY_COLORS[item.priority]?.bg,color:PRIORITY_COLORS[item.priority]?.text}}>{item.priority.toUpperCase()}</span>
                      <span style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,background:STATUS_COLORS[item.status]?.bg,color:STATUS_COLORS[item.status]?.text}}>{item.status.replace(/_/g," ")}</span>
                    </div>
                    <h3 style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:4}}>{item.contract_title}</h3>
                    <p style={{fontSize:13,color:C.muted}}>{item.counterparty||""}{item.risk_level?` · Risk: ${item.risk_level}`:""}</p>
                  </div>
                  {item.due_date && (
                    <div style={{fontSize:12,color:C.error,fontWeight:600}}>
                      Due: {new Date(item.due_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short"})}
                    </div>
                  )}
                </div>
                {item.notes && <div style={{padding:"10px 14px",background:C.bg,borderRadius:8,fontSize:13,color:C.body,marginBottom:16}}>📝 {item.notes}</div>}
                <div style={{display:"flex",gap:10}}>
                  <Link href={`/dashboard/contracts/${item.contract_id}`} style={{padding:"8px 16px",border:`1px solid ${C.border}`,borderRadius:8,textDecoration:"none",fontSize:13,fontWeight:600,color:C.body}}>View contract</Link>
                  {item.status==="pending" && <button onClick={()=>startReview(item.review_id)} style={{padding:"8px 16px",border:"none",background:C.primaryLight,borderRadius:8,fontSize:13,fontWeight:600,color:C.primary,cursor:"pointer"}}>Start review</button>}
                  {item.status==="in_review" && <button onClick={()=>setModal({reviewId:item.review_id,title:item.contract_title})} style={{padding:"8px 16px",border:"none",background:C.primary,borderRadius:8,fontSize:13,fontWeight:600,color:"white",cursor:"pointer"}}>Submit decision →</button>}
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {tab==="all" && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden"}}>
          {loading ? <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading...</div>
          : all.length===0 ? <div style={{padding:60,textAlign:"center",color:C.muted}}>No reviews yet</div>
          : (
            <table style={{width:"100%",borderCollapse:"collapse"}}>
              <thead><tr style={{borderBottom:`1px solid ${C.border}`}}>
                {["Contract","Reviewer","Priority","Status","Decision","Date"].map(h=>(
                  <th key={h} style={{padding:"10px 20px",textAlign:"left",fontSize:12,fontWeight:600,color:C.muted,textTransform:"uppercase"}}>{h}</th>
                ))}
              </tr></thead>
              <tbody>{all.map(r=>(
                <tr key={r.id} style={{borderBottom:`1px solid ${C.border}`}}>
                  <td style={{padding:"12px 20px"}}>
                    <Link href={`/dashboard/contracts/${r.contract_id}`} style={{fontSize:14,fontWeight:600,color:C.heading,textDecoration:"none"}}>{r.contract_title}</Link>
                    {r.risk_level && <div style={{fontSize:11,color:C.muted,marginTop:2}}>{r.risk_level} risk</div>}
                  </td>
                  <td style={{padding:"12px 20px",fontSize:13,color:C.body}}>{r.reviewer_email}</td>
                  <td style={{padding:"12px 20px"}}><span style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,background:PRIORITY_COLORS[r.priority]?.bg,color:PRIORITY_COLORS[r.priority]?.text}}>{r.priority}</span></td>
                  <td style={{padding:"12px 20px"}}><span style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,background:STATUS_COLORS[r.status]?.bg,color:STATUS_COLORS[r.status]?.text}}>{r.status.replace(/_/g," ")}</span></td>
                  <td style={{padding:"12px 20px",fontSize:13,color:r.decision==="approved"?C.success:r.decision==="rejected"?C.error:C.muted}}>{r.decision||"—"}</td>
                  <td style={{padding:"12px 20px",fontSize:12,color:C.muted}}>{new Date(r.created_at).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}</td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      )}

      {/* Decision modal */}
      {modal && (
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:100}}>
          <div style={{background:C.surface,borderRadius:16,padding:32,width:480,boxShadow:"0 20px 60px rgba(0,0,0,0.2)"}}>
            <h2 style={{fontSize:18,fontWeight:700,color:C.heading,marginBottom:4}}>Submit Decision</h2>
            <p style={{fontSize:13,color:C.muted,marginBottom:24}}>{modal.title}</p>
            <div style={{display:"flex",gap:10,marginBottom:20}}>
              {[{v:"approved",l:"✅ Approve",c:C.success},{v:"rejected",l:"❌ Reject",c:C.error},{v:"revision_needed",l:"🔄 Revision",c:C.warning}].map(opt=>(
                <button key={opt.v} onClick={()=>setDecision(opt.v)}
                  style={{flex:1,padding:"10px",border:`2px solid ${decision===opt.v?opt.c:C.border}`,borderRadius:8,
                    background:decision===opt.v?`${opt.c}15`:"none",color:decision===opt.v?opt.c:C.muted,
                    fontSize:13,fontWeight:600,cursor:"pointer"}}>
                  {opt.l}
                </button>
              ))}
            </div>
            <textarea value={notes} onChange={e=>setNotes(e.target.value)} placeholder="Add notes..." rows={3}
              style={{width:"100%",padding:"10px 14px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13,resize:"vertical",marginBottom:20,outline:"none"}}/>
            <div style={{display:"flex",gap:10,justifyContent:"flex-end"}}>
              <button onClick={()=>{setModal(null);setDecision("");setNotes("");}}
                style={{padding:"10px 20px",border:`1px solid ${C.border}`,borderRadius:8,background:"none",fontSize:14,cursor:"pointer"}}>Cancel</button>
              <button onClick={submitDecision} disabled={!decision||submitting}
                style={{padding:"10px 20px",border:"none",borderRadius:8,background:!decision||submitting?"#D1D5DB":C.primary,color:"white",fontSize:14,fontWeight:600,cursor:!decision?"not-allowed":"pointer"}}>
                {submitting?"Submitting...":"Submit"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
