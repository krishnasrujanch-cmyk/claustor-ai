"use client";
export const dynamic = "force-dynamic";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { getToken } from "@/lib/api";
import { C } from "@/lib/design-tokens";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// Priority uses filled pills
const PRIORITY_META: Record<string,{bg:string,text:string,label:string}> = {
  urgent: {bg:"#FEF2F2",text:"#DC2626",label:"🔴 URGENT"},
  high:   {bg:"#FFFBEB",text:"#D97706",label:"🟡 HIGH"},
  normal: {bg:"#E6F0FF",text:"#0066FF",label:"🔵 NORMAL"},
  low:    {bg:"#F0FDF4",text:"#16A34A",label:"🟢 LOW"},
};

// Status uses outline-style pills — distinct from priority
const STATUS_META: Record<string,{bg:string,text:string,border:string,label:string,icon:string}> = {
  pending:         {bg:"#FFFBEB",text:"#92400E",border:"#F59E0B",label:"Pending",   icon:"⏳"},
  in_review:       {bg:"#EFF6FF",text:"#1E40AF",border:"#3B82F6",label:"In Review", icon:"🔍"},
  approved:        {bg:"#F0FDF4",text:"#166534",border:"#22C55E",label:"Approved",  icon:"✅"},
  rejected:        {bg:"#FEF2F2",text:"#991B1B",border:"#EF4444",label:"Rejected",  icon:"❌"},
  revision_needed: {bg:"#FFF7ED",text:"#9A3412",border:"#F97316",label:"Revision",  icon:"🔄"},
};

const RISK_META: Record<string,{dot:string,text:string}> = {
  high:   {dot:"#EF4444",text:"#DC2626"},
  medium: {dot:"#F59E0B",text:"#D97706"},
  low:    {dot:"#22C55E",text:"#16A34A"},
};

function PriorityBadge({priority}:{priority:string}) {
  const m = PRIORITY_META[priority]||PRIORITY_META.normal;
  return (
    <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,
      background:m.bg,color:m.text,letterSpacing:"0.04em"}}>
      {m.label}
    </span>
  );
}

function StatusBadge({status}:{status:string}) {
  const m = STATUS_META[status]||{bg:"#F3F4F6",text:"#6B7280",border:"#D1D5DB",label:status,icon:"·"};
  return (
    <span style={{fontSize:11,fontWeight:600,padding:"3px 10px",borderRadius:20,
      background:m.bg,color:m.text,border:`1px solid ${m.border}30`,
      letterSpacing:"0.02em"}}>
      {m.icon} {m.label}
    </span>
  );
}

function SlaTag({dueDate,createdAt,status}:{dueDate?:string,createdAt:string,status:string}) {
  const now = Date.now();
  const created = new Date(createdAt).getTime();
  const pendingDays = Math.floor((now-created)/(1000*60*60*24));

  if (["approved","rejected","revision_needed"].includes(status)) {
    return (
      <span style={{fontSize:11,color:C.muted}}>
        Completed {new Date(createdAt).toLocaleDateString("en-IN",{day:"2-digit",month:"short"})}
      </span>
    );
  }
  if (dueDate) {
    const daysLeft = Math.ceil((new Date(dueDate).getTime()-now)/(1000*60*60*24));
    const color = daysLeft<0?C.error:daysLeft<=2?C.warning:C.muted;
    return (
      <span style={{fontSize:11,fontWeight:600,color}}>
        {daysLeft<0?`Overdue by ${Math.abs(daysLeft)}d`:
         daysLeft===0?"Due today":
         daysLeft===1?"Due tomorrow":`Due in ${daysLeft}d`}
        {" · "}{new Date(dueDate).toLocaleDateString("en-IN",{day:"2-digit",month:"short"})}
      </span>
    );
  }
  return (
    <span style={{fontSize:11,color:C.muted}}>
      Pending {pendingDays}d
    </span>
  );
}

export default function ReviewsPage() {
  const router = useRouter();
  const { user: currentUser } = useAuthStore();
  const isAdmin = ["super_admin","dept_admin","contract_manager"].includes(currentUser?.role||"");

  const [queue, setQueue]     = useState<any[]>([]);
  const [all, setAll]         = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<string>("my-queue");
  const [search, setSearch]   = useState("");
  const [modal, setModal]     = useState<{reviewId:string;title:string}|null>(null);
  const [decision, setDecision]     = useState("");
  const [notes, setNotes]           = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    setLoading(true);
    const token = getToken();
    const h = {Authorization:`Bearer ${token}`};
    try {
      const [qR, aR] = await Promise.all([
        fetch(`${API}/api/v1/reviews/my-queue`,{headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/reviews/?assigned_to_me=true`,{headers:h}).then(r=>r.json()),
      ]);
      setQueue(qR.queue||[]);
      // For legal reviewer: show all their reviews (pending + completed)
      setAll(aR.reviews||[]);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(()=>{ load(); },[]);

  // Filter counts for stat tabs
  const counts = useMemo(()=>({
    "my-queue":        queue.length,
    pending:           all.filter(r=>r.status==="pending").length,
    in_review:         all.filter(r=>r.status==="in_review").length,
    approved:          all.filter(r=>r.status==="approved").length,
    rejected:          all.filter(r=>r.status==="rejected").length,
    revision_needed:   all.filter(r=>r.status==="revision_needed").length,
  }),[queue,all]);

  // Filtered display list
  const displayList = useMemo(()=>{
    let list: any[] = [];
    if (activeFilter==="my-queue") {
      list = queue;
    } else {
      list = all.filter(r=>r.status===activeFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(r=>
        (r.contract_title||"").toLowerCase().includes(q) ||
        (r.counterparty||"").toLowerCase().includes(q) ||
        (r.reviewer_email||"").toLowerCase().includes(q)
      );
    }
    return list;
  },[activeFilter,queue,all,search]);

  const startReview = async (id:string) => {
    const token = getToken();
    const r = await fetch(`${API}/api/v1/reviews/${id}/start`,
      {method:"POST",headers:{Authorization:`Bearer ${token}`}});
    if(r.ok) {
      setQueue(prev=>prev.map(item=>
        item.review_id===id?{...item,status:"in_review"}:item));
      setAll(prev=>prev.map(item=>
        item.id===id?{...item,status:"in_review"}:item));
    }
  };

  const submitDecision = async () => {
    if(!modal||!decision) return;
    setSubmitting(true);
    const token = getToken();
    try {
      const r = await fetch(`${API}/api/v1/reviews/${modal.reviewId}/decide`,{
        method:"POST",
        headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
        body:JSON.stringify({decision,decision_notes:notes}),
      });
      if(r.ok) {
        const rid = modal.reviewId;
        setModal(null); setDecision(""); setNotes("");
        setQueue(prev=>prev.filter(r=>r.review_id!==rid));
        setAll(prev=>prev.map(r=>r.id===rid
          ?{...r,status:decision==="approved"?"approved":decision==="rejected"?"rejected":"revision_needed",decision}
          :r));
      }
    } finally { setSubmitting(false); }
  };

  // Stat filter tabs
  const TABS = [
    {key:"my-queue",        label:"My Queue",     icon:"👤"},
    {key:"pending",         label:"Pending",      icon:"⏳"},
    {key:"in_review",       label:"In Review",    icon:"🔍"},
    {key:"approved",        label:"Approved",     icon:"✅"},
    {key:"rejected",        label:"Rejected",     icon:"❌"},
    {key:"revision_needed", label:"Revision",     icon:"🔄"},
  ];  // All users see all status tabs for their own reviews

  return (
    <div style={{padding:"28px 32px",maxWidth:1200,margin:"0 auto"}}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div style={{display:"flex",justifyContent:"space-between",
        alignItems:"flex-start",marginBottom:24}}>
        <div>
          <h1 style={{fontSize:22,fontWeight:800,color:C.heading,marginBottom:4}}>
            Review Workflow
          </h1>
          <p style={{fontSize:13,color:C.muted}}>
            Manage contract reviews and approvals
          </p>
        </div>
        {isAdmin && (
          <button onClick={()=>router.push("/dashboard/contracts")}
            style={{padding:"10px 20px",background:C.primary,color:"white",
              border:"none",borderRadius:10,fontSize:13,fontWeight:600,
              cursor:"pointer",boxShadow:"0 2px 8px rgba(91,75,255,0.3)"}}>
            + Assign Review
          </button>
        )}
      </div>

      {/* ── Clickable Stat Tabs ──────────────────────────────────────────── */}
      <div style={{display:"grid",
        gridTemplateColumns:`repeat(${TABS.length},1fr)`,
        gap:12,marginBottom:20}}>
        {TABS.map(tab=>{
          const count = counts[tab.key as keyof typeof counts]||0;
          const active = activeFilter===tab.key;
          const sm = STATUS_META[tab.key]||{bg:C.primaryLight,text:C.primary,border:C.primary};
          return (
            <button key={tab.key} onClick={()=>setActiveFilter(tab.key)}
              style={{padding:"16px 20px",border:`2px solid ${active?C.primary:C.border}`,
                borderRadius:12,background:active?C.primaryLight:C.surface,
                cursor:"pointer",textAlign:"left",transition:"all 0.15s",
                boxShadow:active?"0 0 0 3px rgba(91,75,255,0.1)":"none"}}>
              <div style={{fontSize:12,color:active?C.primary:C.muted,
                fontWeight:600,marginBottom:6,display:"flex",alignItems:"center",gap:4}}>
                <span>{tab.icon}</span>
                {tab.label}
              </div>
              <div style={{fontSize:28,fontWeight:800,
                color:active?C.primary:C.heading,lineHeight:1}}>
                {count}
              </div>
            </button>
          );
        })}
      </div>

      {/* ── Search ───────────────────────────────────────────────────────── */}
      <div style={{position:"relative",marginBottom:20}}>
        <span style={{position:"absolute",left:12,top:"50%",
          transform:"translateY(-50%)",color:C.muted,fontSize:14}}>🔍</span>
        <input value={search} onChange={e=>setSearch(e.target.value)}
          placeholder="Search reviews by contract, counterparty, reviewer..."
          style={{width:"100%",padding:"10px 12px 10px 36px",
            border:`1.5px solid ${C.border}`,borderRadius:10,
            fontSize:13,background:C.surface,boxSizing:"border-box",
            outline:"none"}}/>
        {search && (
          <button onClick={()=>setSearch("")}
            style={{position:"absolute",right:12,top:"50%",
              transform:"translateY(-50%)",border:"none",background:"none",
              cursor:"pointer",color:C.muted,fontSize:14}}>✕</button>
        )}
      </div>

      {/* ── Review Cards ─────────────────────────────────────────────────── */}
      {loading ? (
        <div style={{textAlign:"center",padding:60,color:C.muted}}>
          <div style={{fontSize:24,marginBottom:8}}>⏳</div>
          Loading reviews...
        </div>
      ) : displayList.length===0 ? (
        <div style={{textAlign:"center",padding:80,background:C.surface,
          border:`1px solid ${C.border}`,borderRadius:16}}>
          <div style={{fontSize:48,marginBottom:12}}>
            {activeFilter==="my-queue"?"🎉":"🔍"}
          </div>
          <div style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:6}}>
            {activeFilter==="my-queue"?"Queue is empty":"No reviews found"}
          </div>
          <div style={{fontSize:13,color:C.muted}}>
            {activeFilter==="my-queue"?"No contracts assigned for review":"Try adjusting your search or filter"}
          </div>
        </div>
      ) : (
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          {displayList.map(item=>{
            const rid = item.review_id||item.id;
            const cid = item.contract_id;
            const title = item.contract_title||"Contract";
            const status = item.status||"pending";
            const priority = item.priority||"normal";
            const sm = STATUS_META[status];
            const pm = PRIORITY_META[priority]||PRIORITY_META.normal;
            const rm = RISK_META[item.risk_level||"low"];
            const isCompleted = ["approved","rejected","revision_needed"].includes(status);
            const isPending = status==="pending";
            const isInReview = status==="in_review";

            return (
              <div key={rid}
                style={{background:C.surface,borderRadius:14,overflow:"hidden",
                  border:`1px solid ${C.border}`,
                  borderLeft:`4px solid ${isPending?C.warning:isInReview?C.primary:isCompleted&&status==="approved"?C.success:isCompleted&&status==="rejected"?C.error:C.warning}`,
                  boxShadow:"0 1px 4px rgba(0,0,0,0.05)",
                  transition:"box-shadow 0.15s"}}
                onMouseEnter={e=>e.currentTarget.style.boxShadow="0 4px 16px rgba(0,0,0,0.08)"}
                onMouseLeave={e=>e.currentTarget.style.boxShadow="0 1px 4px rgba(0,0,0,0.05)"}>

                <div style={{padding:"16px 20px"}}>
                  {/* Top row: badges + SLA */}
                  <div style={{display:"flex",justifyContent:"space-between",
                    alignItems:"center",marginBottom:10}}>
                    <div style={{display:"flex",gap:6,alignItems:"center",flexWrap:"wrap"}}>
                      <PriorityBadge priority={priority}/>
                      <StatusBadge status={status}/>
                    </div>
                    <SlaTag dueDate={item.due_date} createdAt={item.created_at||new Date().toISOString()} status={status}/>
                  </div>

                  {/* Main content row */}
                  <div style={{display:"flex",justifyContent:"space-between",
                    alignItems:"flex-start",gap:16}}>

                    {/* Left: Contract info */}
                    <div style={{flex:1,minWidth:0}}>
                      <h3 onClick={()=>router.push(`/dashboard/contracts/${cid}`)}
                        style={{fontSize:15,fontWeight:700,color:C.heading,
                          marginBottom:4,cursor:"pointer",lineHeight:1.3,
                          overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}
                        title={title}>
                        {title}
                      </h3>
                      <div style={{display:"flex",alignItems:"center",gap:8,
                        fontSize:12,color:C.muted,flexWrap:"wrap",marginBottom:8}}>
                        <span>{item.counterparty||"Unknown counterparty"}</span>
                        {item.risk_level && (
                          <>
                            <span>·</span>
                            <span style={{display:"flex",alignItems:"center",gap:4,fontWeight:600,color:rm.text}}>
                              <span style={{width:6,height:6,borderRadius:"50%",
                                background:rm.dot,display:"inline-block"}}/>
                              {item.risk_level.toUpperCase()} RISK
                            </span>
                          </>
                        )}
                        {item.reviewer_email && (
                          <>
                            <span>·</span>
                            <span>👤 {item.reviewer_email.split("@")[0]}</span>
                          </>
                        )}
                      </div>

                      {/* Metadata chips */}
                      <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
                        {item.contract_value && (
                          <span style={{fontSize:12,fontWeight:600,
                            padding:"3px 10px",borderRadius:20,
                            background:"#F8F9FF",border:`1px solid ${C.border}`,
                            color:C.body}}>
                            💰 {item.contract_currency||"₹"}
                            {Number(item.contract_value).toLocaleString("en-IN")}
                          </span>
                        )}
                        {(item.clause_flags?.length>0) && (
                          <span style={{fontSize:12,fontWeight:600,
                            padding:"3px 10px",borderRadius:20,
                            background:C.errorLight,border:`1px solid ${C.error}30`,
                            color:C.error}}>
                            🚩 {item.clause_flags.filter((f:any)=>f.action==="flag").length} flagged clauses
                          </span>
                        )}
                        {item.notes && (
                          <span style={{fontSize:12,padding:"3px 10px",borderRadius:20,
                            background:C.bg,border:`1px solid ${C.border}`,
                            color:C.muted,maxWidth:240,
                            overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                            📝 {item.notes}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Right: Primary CTA */}
                    <div style={{display:"flex",flexDirection:"column",
                      alignItems:"flex-end",gap:8,flexShrink:0}}>
                      {/* Single primary action based on state */}
                      {isPending && (
                        <button onClick={()=>startReview(rid)}
                          style={{padding:"9px 20px",background:C.primary,color:"white",
                            border:"none",borderRadius:10,fontSize:13,fontWeight:700,
                            cursor:"pointer",boxShadow:"0 2px 8px rgba(91,75,255,0.3)",
                            whiteSpace:"nowrap"}}>
                          🚀 Start Review →
                        </button>
                      )}
                      {isInReview && (
                        <button onClick={()=>router.push(`/dashboard/reviews/${rid}`)}
                          style={{padding:"9px 20px",background:C.primary,color:"white",
                            border:"none",borderRadius:10,fontSize:13,fontWeight:700,
                            cursor:"pointer",boxShadow:"0 2px 8px rgba(91,75,255,0.3)",
                            whiteSpace:"nowrap"}}>
                          📋 Open Workspace →
                        </button>
                      )}
                      {isCompleted && (
                        <button onClick={()=>router.push(`/dashboard/reviews/${rid}`)}
                          style={{padding:"9px 20px",background:C.bg,color:C.body,
                            border:`1px solid ${C.border}`,borderRadius:10,
                            fontSize:13,fontWeight:600,cursor:"pointer",
                            whiteSpace:"nowrap"}}>
                          View Decision
                        </button>
                      )}
                      {/* Secondary: View contract */}
                      <Link href={`/dashboard/contracts/${cid}`}
                        style={{fontSize:12,color:C.primary,fontWeight:600,
                          textDecoration:"none",padding:"4px 0"}}>
                        View contract →
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Quick Decision Modal ─────────────────────────────────────────── */}
      {modal && (
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",
          display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000}}>
          <div style={{background:C.surface,borderRadius:16,padding:28,
            width:"100%",maxWidth:480,boxShadow:"0 20px 60px rgba(0,0,0,0.2)"}}>
            <h3 style={{fontSize:18,fontWeight:700,color:C.heading,marginBottom:4}}>
              Submit Decision
            </h3>
            <p style={{fontSize:13,color:C.muted,marginBottom:20}}>
              {modal.title}
            </p>
            <div style={{display:"flex",gap:8,marginBottom:16}}>
              {[
                {v:"approved",     label:"✅ Approve",  bg:C.success},
                {v:"rejected",     label:"❌ Reject",   bg:C.error},
                {v:"revision_needed",label:"🔄 Revision",bg:C.warning},
              ].map(opt=>(
                <button key={opt.v} onClick={()=>setDecision(opt.v)}
                  style={{flex:1,padding:"10px 8px",border:`2px solid ${decision===opt.v?opt.bg:C.border}`,
                    borderRadius:10,background:decision===opt.v?`${opt.bg}15`:"none",
                    cursor:"pointer",fontSize:12,fontWeight:700,
                    color:decision===opt.v?opt.bg:C.muted}}>
                  {opt.label}
                </button>
              ))}
            </div>
            <textarea value={notes} onChange={e=>setNotes(e.target.value)}
              placeholder="Add decision notes (optional)..."
              style={{width:"100%",height:80,padding:"10px 12px",
                border:`1.5px solid ${C.border}`,borderRadius:10,
                fontSize:13,resize:"vertical",outline:"none",
                boxSizing:"border-box",fontFamily:"inherit"}}/>
            <div style={{display:"flex",gap:10,marginTop:16}}>
              <button onClick={()=>setModal(null)}
                style={{flex:1,padding:"10px",border:`1px solid ${C.border}`,
                  borderRadius:10,background:"none",cursor:"pointer",
                  fontSize:13,color:C.body}}>
                Cancel
              </button>
              <button onClick={submitDecision} disabled={!decision||submitting}
                style={{flex:2,padding:"10px",border:"none",borderRadius:10,
                  background:decision?C.primary:"#D1D5DB",color:"white",
                  cursor:decision?"pointer":"not-allowed",fontSize:13,fontWeight:700}}>
                {submitting?"Submitting...":"Submit Decision →"}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
