"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getToken } from "@/lib/api";
import { C } from "@/lib/design-tokens";

const API = "http://localhost:8000";
const RISK_COLOR: Record<string,string> = {high:C.error,medium:C.warning,low:C.success};

type ClauseFlag = {clause_id:string;action:"accept"|"flag"|"comment";comment?:string};

export default function ReviewWorkspacePage() {
  const { reviewId } = useParams();
  const router = useRouter();

  const [data, setData]               = useState<any>(null);
  const [loading, setLoading]         = useState(true);
  const [flags, setFlags]             = useState<Record<string,ClauseFlag>>({});
  const [decision, setDecision]       = useState("");
  const [decisionNotes, setDecisionNotes] = useState("");
  const [submitting, setSubmitting]   = useState(false);
  const [msg, setMsg]                 = useState("");
  const [expandedId, setExpandedId]   = useState<string|null>(null);
  const [commentId, setCommentId]     = useState<string|null>(null);
  const [commentText, setCommentText] = useState("");
  const [starting, setStarting]       = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/reviews/${reviewId}`,
        {headers:{Authorization:`Bearer ${getToken()}`}});
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail);
      setData(d);
      const existing: Record<string,ClauseFlag> = {};
      for (const f of (d.review.clause_flags||[])) existing[f.clause_id] = f;
      setFlags(existing);
      setDecision(d.review.decision||"");
      setDecisionNotes(d.review.decision_notes||"");
    } catch(e:any) { setMsg(`❌ ${e.message}`); }
    finally { setLoading(false); }
  };

  useEffect(()=>{load();},[reviewId]);

  const startReview = async () => {
    setStarting(true);
    await fetch(`${API}/api/v1/reviews/${reviewId}/start`,
      {method:"POST",headers:{Authorization:`Bearer ${getToken()}`}});
    await load();
    setStarting(false);
  };

  const flag = (clauseId:string, action:"accept"|"flag"|"comment", comment?:string) =>
    setFlags(prev=>({...prev,[clauseId]:{clause_id:clauseId,action,comment}}));

  const submitDecision = async () => {
    if (!decision){setMsg("❌ Select a decision first");return;}
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/api/v1/reviews/${reviewId}/decide`,{
        method:"POST",
        headers:{Authorization:`Bearer ${getToken()}`,"Content-Type":"application/json"},
        body:JSON.stringify({decision,decision_notes:decisionNotes,clause_flags:Object.values(flags)}),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail);
      setMsg("✅ Decision submitted!");
      setTimeout(()=>router.push("/dashboard/reviews"),1500);
    } catch(e:any){setMsg(`❌ ${e.message}`);}
    finally{setSubmitting(false);}
  };

  if (loading) return <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading review workspace...</div>;
  if (!data)   return <div style={{padding:40,textAlign:"center",color:C.error}}>{msg||"Review not found"}</div>;

  const {review,contract,clauses,reviewer} = data;
  const isCompleted = ["approved","rejected","revision_needed"].includes(review.status);
  const reviewedCount = Object.keys(flags).length;
  const totalClauses  = clauses.length;
  const flaggedCount  = Object.values(flags).filter((f:any)=>f.action==="flag").length;
  const acceptedCount = Object.values(flags).filter((f:any)=>f.action==="accept").length;
  const commentCount  = Object.values(flags).filter((f:any)=>f.action==="comment").length;

  return (
    <div style={{height:"100vh",display:"flex",flexDirection:"column",background:C.bg,overflow:"hidden"}}>

      {/* Top bar */}
      <div style={{background:C.surface,borderBottom:`1px solid ${C.border}`,
        padding:"10px 20px",display:"flex",alignItems:"center",gap:12,flexShrink:0}}>
        <button onClick={()=>router.push("/dashboard/reviews")}
          style={{background:"none",border:"none",cursor:"pointer",fontSize:18,color:C.muted,padding:"4px 8px"}}>
          ← Back
        </button>
        <div style={{flex:1}}>
          <div style={{fontSize:15,fontWeight:800,color:C.heading}}>{contract.title}</div>
          <div style={{fontSize:11,color:C.muted}}>
            {contract.counterparty} · {contract.contract_type} ·
            <span style={{fontWeight:700,color:RISK_COLOR[contract.risk_level]||C.muted,marginLeft:4}}>
              {(contract.risk_level||"").toUpperCase()} RISK
            </span>
          </div>
        </div>
        <div style={{display:"flex",gap:20}}>
          {[
            {v:reviewedCount+"/"+totalClauses,l:"Reviewed",c:C.primary},
            {v:acceptedCount,l:"Accepted",c:C.success},
            {v:flaggedCount,l:"Flagged",c:C.error},
            {v:commentCount,l:"Noted",c:C.warning},
          ].map(s=>(
            <div key={s.l} style={{textAlign:"center"}}>
              <div style={{fontSize:16,fontWeight:800,color:s.c}}>{s.v}</div>
              <div style={{fontSize:10,color:C.muted}}>{s.l}</div>
            </div>
          ))}
        </div>
        <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,
          background:review.priority==="high"?"#FEF2F2":C.primaryLight,
          color:review.priority==="high"?C.error:C.primary}}>
          {(review.priority||"normal").toUpperCase()}
        </span>
        {review.status==="pending" && (
          <button onClick={startReview} disabled={starting}
            style={{padding:"8px 16px",background:C.primary,color:"white",border:"none",
              borderRadius:8,fontSize:13,fontWeight:600,cursor:"pointer"}}>
            {starting?"...":"▶ Start Review"}
          </button>
        )}
      </div>

      {/* Body: 2 columns */}
      <div style={{flex:1,display:"grid",gridTemplateColumns:"1fr 360px",overflow:"hidden"}}>

        {/* LEFT: Clauses */}
        <div style={{overflow:"auto",padding:"20px 24px",display:"flex",flexDirection:"column",gap:10}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <div style={{fontSize:14,fontWeight:700,color:C.heading}}>
              Contract Clauses ({totalClauses})
            </div>
            {!isCompleted && (
              <button onClick={()=>{
                const nf = {...flags};
                clauses.filter((c:any)=>c.risk_level==="low").forEach((c:any)=>{
                  if (!nf[c.id]) nf[c.id]={clause_id:c.id,action:"accept"};
                });
                setFlags(nf);
              }} style={{fontSize:11,padding:"4px 12px",background:"#F0FDF4",color:C.success,
                border:`1px solid ${C.success}30`,borderRadius:6,cursor:"pointer",fontWeight:600}}>
                ✓ Auto-accept all LOW risk
              </button>
            )}
          </div>

          {clauses.map((clause:any)=>{
            const f = flags[clause.id];
            const bc = f?.action==="accept"?C.success:f?.action==="flag"?C.error:f?.action==="comment"?C.warning:C.border;
            const bg = f?.action==="accept"?"#F0FDF4":f?.action==="flag"?"#FEF2F2":f?.action==="comment"?"#FFFBEB":C.surface;
            const isExpanded = expandedId===clause.id;
            const isCommenting = commentId===clause.id;

            return (
              <div key={clause.id} style={{background:bg,border:`2px solid ${bc}`,borderRadius:10,padding:14}}>
                {/* Header */}
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
                  <div style={{display:"flex",gap:8,alignItems:"center"}}>
                    <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:20,
                      background:`${RISK_COLOR[clause.risk_level]||C.muted}18`,
                      color:RISK_COLOR[clause.risk_level]||C.muted}}>
                      {(clause.risk_level||"").toUpperCase()}
                    </span>
                    <span style={{fontSize:13,fontWeight:600,color:C.heading,textTransform:"capitalize"}}>
                      {(clause.clause_type||"").replace(/_/g," ")}
                    </span>
                    {clause.risk_score!=null&&(
                      <span style={{fontSize:10,color:C.muted,background:C.bg,
                        padding:"1px 6px",borderRadius:10}}>
                        {clause.risk_score}/100
                      </span>
                    )}
                  </div>
                  {!isCompleted ? (
                    <div style={{display:"flex",gap:4}}>
                      <button onClick={()=>flag(clause.id,"accept")}
                        style={{padding:"3px 10px",fontSize:11,fontWeight:700,border:"none",borderRadius:6,cursor:"pointer",
                          background:f?.action==="accept"?C.success:"#F0FDF4",color:f?.action==="accept"?"white":C.success}}>
                        ✓
                      </button>
                      <button onClick={()=>flag(clause.id,"flag")}
                        style={{padding:"3px 10px",fontSize:11,fontWeight:700,border:"none",borderRadius:6,cursor:"pointer",
                          background:f?.action==="flag"?C.error:"#FEF2F2",color:f?.action==="flag"?"white":C.error}}>
                        🚩
                      </button>
                      <button onClick={()=>{setCommentId(clause.id);setCommentText(f?.comment||"");}}
                        style={{padding:"3px 10px",fontSize:11,fontWeight:700,border:"none",borderRadius:6,cursor:"pointer",
                          background:f?.action==="comment"?C.warning:"#FFFBEB",color:f?.action==="comment"?"white":C.warning}}>
                        💬
                      </button>
                    </div>
                  ) : f && (
                    <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:20,
                      background:f.action==="accept"?"#F0FDF4":f.action==="flag"?"#FEF2F2":"#FFFBEB",
                      color:f.action==="accept"?C.success:f.action==="flag"?C.error:C.warning}}>
                      {f.action==="accept"?"✓ Accepted":f.action==="flag"?"🚩 Flagged":"💬 Noted"}
                    </span>
                  )}
                </div>

                {/* Summary */}
                <p style={{fontSize:13,color:C.body,margin:"0 0 6px",lineHeight:1.5}}>{clause.summary}</p>

                {/* Comment display */}
                {f?.comment&&<div style={{fontSize:12,color:C.warning,background:"#FFFBEB",
                  padding:"5px 8px",borderRadius:6,marginBottom:6}}>💬 {f.comment}</div>}

                {/* Expand raw text */}
                {clause.raw_text&&(
                  <button onClick={()=>setExpandedId(isExpanded?null:clause.id)}
                    style={{fontSize:11,color:C.primary,background:"none",border:"none",
                      cursor:"pointer",padding:0,marginBottom:isExpanded?8:0}}>
                    {isExpanded?"▲ Hide full text":"▼ Show full text"}
                  </button>
                )}
                {isExpanded&&clause.raw_text&&(
                  <div style={{padding:10,background:"#F9FAFB",borderRadius:8,
                    border:`1px solid ${C.border}`,marginBottom:8}}>
                    <div style={{fontSize:10,fontWeight:700,color:C.muted,marginBottom:6}}>FULL TEXT</div>
                    <p style={{fontSize:12,color:C.body,margin:0,lineHeight:1.6,whiteSpace:"pre-wrap"}}>
                      {clause.raw_text}
                    </p>
                  </div>
                )}

                {/* Comment input */}
                {isCommenting&&!isCompleted&&(
                  <div style={{marginTop:8}}>
                    <textarea value={commentText} onChange={e=>setCommentText(e.target.value)}
                      placeholder="Add note..." rows={2}
                      style={{width:"100%",padding:"7px 10px",border:`1px solid ${C.border}`,
                        borderRadius:8,fontSize:12,resize:"none",boxSizing:"border-box"}}/>
                    <div style={{display:"flex",gap:6,marginTop:4}}>
                      <button onClick={()=>{flag(clause.id,"comment",commentText);setCommentId(null);}}
                        style={{padding:"4px 12px",background:C.warning,color:"white",border:"none",
                          borderRadius:6,fontSize:11,fontWeight:600,cursor:"pointer"}}>Save</button>
                      <button onClick={()=>setCommentId(null)}
                        style={{padding:"4px 10px",background:"#F3F4F6",border:"none",
                          borderRadius:6,fontSize:11,cursor:"pointer",color:C.muted}}>Cancel</button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* RIGHT: Decision panel */}
        <div style={{borderLeft:`1px solid ${C.border}`,background:C.surface,
          display:"flex",flexDirection:"column",overflow:"auto"}}>

          {/* Summary */}
          <div style={{padding:16,borderBottom:`1px solid ${C.border}`}}>
            <div style={{fontSize:13,fontWeight:700,color:C.heading,marginBottom:10}}>Contract Details</div>
            {[
              ["Value",  contract.contract_value?`${contract.currency||"USD"} ${Number(contract.contract_value).toLocaleString()}`:"—"],
              ["Effective",contract.effective_date||"—"],
              ["Expires",  contract.expiry_date||"—"],
              ["Type",     contract.contract_type||"—"],
            ].map(([l,v])=>(
              <div key={l} style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:6}}>
                <span style={{color:C.muted}}>{l}</span>
                <span style={{color:C.body,fontWeight:600}}>{v}</span>
              </div>
            ))}
            {contract.summary&&(
              <p style={{fontSize:11,color:C.body,marginTop:8,lineHeight:1.5,
                padding:8,background:C.bg,borderRadius:6}}>{contract.summary}</p>
            )}
          </div>

          {/* Progress bar */}
          <div style={{padding:16,borderBottom:`1px solid ${C.border}`}}>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:6}}>
              <span style={{color:C.muted}}>Review progress</span>
              <span style={{fontWeight:700,color:reviewedCount===totalClauses?C.success:C.primary}}>
                {reviewedCount}/{totalClauses}
              </span>
            </div>
            <div style={{height:6,background:C.border,borderRadius:3,marginBottom:12}}>
              <div style={{height:"100%",borderRadius:3,background:
                reviewedCount===totalClauses?C.success:C.primary,
                width:`${totalClauses>0?reviewedCount/totalClauses*100:0}%`,transition:"width 0.3s"}}/>
            </div>
            <div style={{display:"flex",gap:8}}>
              {[{v:acceptedCount,l:"Accepted",c:C.success,bg:"#F0FDF4"},
                {v:flaggedCount,l:"Flagged",c:C.error,bg:"#FEF2F2"},
                {v:commentCount,l:"Noted",c:C.warning,bg:"#FFFBEB"}].map(s=>(
                <div key={s.l} style={{flex:1,textAlign:"center",padding:8,background:s.bg,borderRadius:8}}>
                  <div style={{fontSize:16,fontWeight:800,color:s.c}}>{s.v}</div>
                  <div style={{fontSize:10,color:s.c}}>{s.l}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Decision */}
          <div style={{padding:16,flex:1}}>
            <div style={{fontSize:13,fontWeight:700,color:C.heading,marginBottom:12}}>
              {isCompleted?"Decision":"Submit Decision"}
            </div>

            {msg&&<div style={{padding:"8px 12px",borderRadius:8,marginBottom:12,fontSize:12,
              background:msg.startsWith("✅")?"#F0FDF4":"#FEF2F2",
              color:msg.startsWith("✅")?C.success:C.error}}>{msg}</div>}

            {isCompleted ? (
              <div style={{padding:14,background:
                review.decision==="approved"?"#F0FDF4":
                review.decision==="rejected"?"#FEF2F2":"#FFFBEB",borderRadius:10}}>
                <div style={{fontSize:15,fontWeight:800,
                  color:review.decision==="approved"?C.success:
                    review.decision==="rejected"?C.error:C.warning}}>
                  {review.decision==="approved"?"✅ Approved":
                   review.decision==="rejected"?"❌ Rejected":"🔄 Revision Needed"}
                </div>
                {review.decision_notes&&<p style={{fontSize:12,color:C.body,marginTop:8}}>{review.decision_notes}</p>}
              </div>
            ) : (
              <>
                <div style={{display:"flex",flexDirection:"column",gap:8,marginBottom:12}}>
                  {[{v:"approved",l:"✅ Approve",c:C.success},
                    {v:"rejected",l:"❌ Reject",c:C.error},
                    {v:"revision_needed",l:"🔄 Request Revision",c:C.warning}].map(opt=>(
                    <button key={opt.v} onClick={()=>setDecision(opt.v)}
                      style={{padding:"10px 14px",border:`2px solid ${decision===opt.v?opt.c:C.border}`,
                        borderRadius:10,background:decision===opt.v?`${opt.c}12`:"white",
                        color:decision===opt.v?opt.c:C.body,fontWeight:decision===opt.v?700:400,
                        cursor:"pointer",textAlign:"left",fontSize:13}}>
                      {opt.l}
                    </button>
                  ))}
                </div>

                <textarea value={decisionNotes} onChange={e=>setDecisionNotes(e.target.value)}
                  placeholder="Decision notes..." rows={3}
                  style={{width:"100%",padding:"8px 10px",border:`1px solid ${C.border}`,
                    borderRadius:8,fontSize:12,resize:"none",marginBottom:10,boxSizing:"border-box"}}/>

                {flaggedCount>0&&(
                  <div style={{padding:"8px 12px",background:"#FEF2F2",borderRadius:8,
                    fontSize:11,color:C.error,marginBottom:10}}>
                    ⚠️ {flaggedCount} flagged clause(s) — consider rejecting or revision
                  </div>
                )}

                <button onClick={submitDecision}
                  disabled={!decision||submitting||review.status==="pending"}
                  style={{width:"100%",padding:"11px",border:"none",borderRadius:10,
                    background:!decision||review.status==="pending"?"#D1D5DB":C.primary,
                    color:"white",fontSize:13,fontWeight:700,
                    cursor:!decision||review.status==="pending"?"not-allowed":"pointer"}}>
                  {submitting?"Submitting...":
                   review.status==="pending"?"Start review first":
                   "Submit Decision →"}
                </button>

                {review.status==="pending"&&(
                  <p style={{fontSize:10,color:C.muted,textAlign:"center",marginTop:6}}>
                    Press "Start Review" to begin
                  </p>
                )}
              </>
            )}
          </div>

          <div style={{padding:"10px 16px",borderTop:`1px solid ${C.border}`,fontSize:11,color:C.muted}}>
            Assigned to: {reviewer?.name||reviewer?.email} ·
            Due: {review.due_date?new Date(review.due_date).toLocaleDateString("en-IN"):"No deadline"}
          </div>
        </div>
      </div>
    </div>
  );
}
