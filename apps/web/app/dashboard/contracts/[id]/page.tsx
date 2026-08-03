"use client";
import { useAuthStore } from "@/store/auth";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { contracts as contractsAPI, chat as chatAPI, Contract, Clause, getToken } from "@/lib/api";
import { MarkdownText } from "@/components/shared/MarkdownText";
import { C } from "@/lib/design-tokens";

const API = "http://localhost:8000";
function RiskBadge({ level }: { level:string }) {
  const m: Record<string,any> = {
    high:{bg:"#FEF2F2",text:"#DC2626"},
    medium:{bg:"#FFFBEB",text:"#D97706"},
    low:{bg:"#F0FDF4",text:"#16A34A"},
  };
  const c = m[level]||{bg:"#F3F4F6",text:"#6B7280"};
  return <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,background:c.bg,color:c.text,textTransform:"uppercase"}}>{level}</span>;
}


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

function TypingDots() {
  return (
    <span style={{display:"inline-flex",gap:3,alignItems:"center",padding:"4px 0"}}>
      {[0,1,2].map(i=>(
        <span key={i} style={{width:6,height:6,borderRadius:"50%",background:"#6B7280",opacity:0.4,
          animation:`typingDot 1.2s ease-in-out ${i*0.2}s infinite`}}/>
      ))}
    </span>
  );
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

function contractHealth(contract: any): number {
  const riskPenalty = (contract.risk_score || 50);
  const missingPenalty = ((contract.missing_clauses?.length || 0) * 5);
  const clauses = contract.clauses || [];
  const avgPlaybook = clauses.length > 0
    ? clauses.reduce((s: number, c: any) => s + (c.playbook_match || 0.5), 0) / clauses.length
    : 0.5;
  const playboookBonus = Math.round(avgPlaybook * 20);
  return Math.max(0, Math.min(100, 100 - riskPenalty * 0.5 - missingPenalty + playboookBonus));
}

function parseAISummary(summary: string): {label:string,value:string}[] {
  // Extract key facts from summary text
  const bullets: {label:string,value:string}[] = [];
  const patterns = [
    {label:"Scope",       regex:/licens\w+ (.{0,80})/i},
    {label:"Financials",  regex:/(\$[\d,.]+M?|USD[\s\d,.]+M?|INR[\s\d,.]+)/i},
    {label:"Term",        regex:/(\d+[\s-]year|\d+[\s-]month).*?term/i},
    {label:"Royalty",     regex:/(\d+[\s.]?\d*%)\s*royalt/i},
    {label:"Territories", regex:/india|asean|mena|global|worldwide/i},
  ];
  for (const p of patterns) {
    const match = summary.match(p.regex);
    if (match) bullets.push({label:p.label, value:match[0].substring(0,80)});
  }
  return bullets.slice(0,4);
}

export default function ContractDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { user: currentUser } = useAuthStore();
  const canAssign = ["super_admin","dept_admin","contract_manager"].includes(currentUser?.role || "");
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
  const [clauseFlags, setClauseFlags]   = useState<Record<string,any>>({});
  const [versions, setVersions]           = useState<any[]>([]);
  const [showUpload, setShowUpload]       = useState(false);
  const [uploading, setUploading]         = useState(false);
  const [uploadMsg, setUploadMsg]         = useState("");
  const [showRiskTooltip, setShowRiskTooltip] = useState(false);
  const [pdfUrl, setPdfUrl]                   = useState<string|null>(null);
  const [pdfLoading, setPdfLoading]           = useState(false);
  const [assignMsg, setAssignMsg]       = useState("");

  // Analytics state
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // Chat state
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<Array<{role:string;content:string;citations?:any[];groundedness?:number;db_sourced?:boolean}>>([]);
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    const token = getToken();
    fetch(`${API}/api/v1/reviews/?contract_id=${id}`,
      {headers:{Authorization:`Bearer ${token}`}})
    .then(r=>r.json())
    .then(rd=>{
      const flags: Record<string,any> = {};
      for (const rv of (rd.reviews||[])) {
        for (const f of (rv.clause_flags||[])) {
          flags[f.clause_id] = {...f, reviewer: rv.reviewer_email};
        }
      }
      setClauseFlags(flags);
    }).catch(console.error);
  }, [id]);

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

  const loadPdf = async () => {
    if (pdfUrl) return; // already loaded
    setPdfLoading(true);
    const token = getToken();
    try {
      const r = await fetch(`${API}/api/v1/contracts/${id}/download`,
        {headers:{Authorization:`Bearer ${token}`}});
      if (r.ok) {
        const blob = await r.blob();
        setPdfUrl(URL.createObjectURL(blob));
      }
    } catch(e) { console.error(e); }
    finally { setPdfLoading(false); }
  };

  const uploadNewVersion = async (file: File) => {
    setUploading(true); setUploadMsg("");
    const token = typeof window !== "undefined" ? localStorage.getItem("claustor_token") : "";
    const formData = new FormData();
    formData.append("file", file);
    formData.append("parent_contract_id", id);
    formData.append("version_note", `Revision of v${contract?.version_number||1}`);
    try {
      const r = await fetch(`${API}/api/v1/contracts/`, {
        method:"POST",
        headers:{Authorization:`Bearer ${token}`},
        body:formData,
      });
      const d = await r.json();
      if (r.ok) {
        setUploadMsg("✅ New version uploaded! Processing...");
        setTimeout(() => router.push(`/dashboard/contracts/${d.contract_id}`), 1500);
      } else {
        setUploadMsg(`❌ ${d.detail}`);
      }
    } catch(e:any) { setUploadMsg(`❌ ${e.message}`); }
    finally { setUploading(false); }
  };

  const chatAbortRef = typeof window !== "undefined" ? { current: null as AbortController|null } : { current: null };
  const sendChat = async (query?: string) => {
    const q = (query || chatInput).trim();
    if (!q || chatLoading) return;
    setChatInput(""); setChatLoading(true);
    setChatMessages(prev=>[...prev,{role:"user",content:q},{role:"assistant",content:"",isStreaming:true} as any]);
    try {
      const token = getToken();
      const res = await fetch(`${API}/api/v1/chat/stream`,{
        method:"POST",
        headers:{"Authorization":`Bearer ${token}`,"Content-Type":"application/json"},
        body:JSON.stringify({query:q, contract_id:id}),
      });
      if(!res.ok) throw new Error(`HTTP ${res.status}`);
      const reader = res.body!.getReader(); const dec = new TextDecoder();
      let full="", cits:any[]=[], ground:number|undefined, dbSourced=false;
      while(true){
        const{done,value}=await reader.read(); if(done) break;
        for(const line of dec.decode(value,{stream:true}).split("\n")){
          if(!line.startsWith("data: ")) continue;
          try{
            const d=JSON.parse(line.slice(6));
            if(d.type==="token"){full+=d.content;setChatMessages(prev=>{const u=[...prev];u[u.length-1]={...u[u.length-1],content:full};return u;});}
            else if(d.type==="citations") cits=d.citations||[];
            else if(d.type==="meta"){if(d.db_sourced)dbSourced=true;ground=d.groundedness;}
            else if(d.type==="done"){setChatMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:full,citations:cits,groundedness:ground,db_sourced:dbSourced};return u;});}
            else if(d.type==="error"){setChatMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:d.message||"Error"};return u;});}
          }catch{}
        }
      }
    } catch {
      setChatMessages(prev=>{const u=[...prev];u[u.length-1]={role:"assistant",content:"Sorry, could not process that."};return u;});
    } finally { setChatLoading(false); }
  };

  if (loading) return <div style={{height:"100%",display:"flex",alignItems:"center",justifyContent:"center",color:C.muted}}>Loading...</div>;
  if (!contract) return null;

  const highRiskClauses = (contract.clauses||[]).filter((c:any)=>c.risk_level==="high").length;
  const missingCount = contract.missing_clauses?.length || 0;
  const tabs:{id:Tab;label:string}[] = [
    {id:"overview",  label:"Overview"},
    {id:"clauses",   label:`Clauses (${contract.clauses?.length||0})`},
    {id:"analytics", label:highRiskClauses>0?`🔴 Risk Analytics (${highRiskClauses} High)`:"Analytics"},
    {id:"chat",      label:"💬 AI Copilot"},
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
          <div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap",marginTop:6}}>
            {contract.contract_type && (
              <span style={{fontSize:12,color:C.body,background:C.bg,padding:"3px 10px",
                borderRadius:20,border:`1px solid ${C.border}`,fontWeight:500}}>
                {contract.contract_type}
              </span>
            )}
            {/* Version dropdown — only once */}
            {versions.length > 1 ? (
              <select value={id}
                onChange={e=>router.push("/dashboard/contracts/"+e.target.value)}
                style={{fontSize:12,fontWeight:700,padding:"3px 10px",borderRadius:20,
                  border:"1px solid #0066FF",color:"#0066FF",background:"#E6F0FF",
                  cursor:"pointer"}}>
                {versions.map((v:any)=>(
                  <option key={v.id} value={v.id}>
                    {v.is_latest?"✅ ":""}v{v.version_number||1}
                    {v.review_status?" · "+v.review_status:""}
                  </option>
                ))}
              </select>
            ) : (
              <span style={{fontSize:12,fontWeight:700,padding:"3px 10px",borderRadius:20,
                background:"#E6F0FF",color:"#0066FF"}}>
                v{contract.version||1}
              </span>
            )}
            {/* Risk badge — context-aware */}
            {contract.risk_level && (
              <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,
                background:contract.risk_level==="high"?"#FEF2F2":
                           contract.risk_level==="medium"?"#FFFBEB":"#F0FDF4",
                color:contract.risk_level==="high"?"#DC2626":
                      contract.risk_level==="medium"?"#D97706":"#16A34A",
                textTransform:"uppercase"}}>
                {contract.risk_level==="high"?"🔴":contract.risk_level==="medium"?"🟡":"🟢"} {contract.risk_level} Risk
              </span>
            )}
            {/* Approval badge — neutral when high risk + approved */}
            {contract.review_status==="approved" && (
              <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,
                border:"1px solid #22C55E40",
                background:contract.risk_level==="high"?"#F3F4F6":"#F0FDF4",
                color:contract.risk_level==="high"?"#6B7280":"#16A34A"}}>
                ✅ {contract.risk_level==="high"?"Approved with High-Risk Exceptions":"Approved"}
              </span>
            )}
            {contract.review_status==="rejected" && (
              <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,
                background:"#FEF2F2",color:"#DC2626",border:"1px solid #EF444440"}}>
                ❌ Rejected
              </span>
            )}
            {contract.review_status==="revision_needed" && (
              <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,
                background:"#FFFBEB",color:"#D97706",border:"1px solid #F59E0B40"}}>
                🔄 Revision Required
              </span>
            )}
          </div>
        </div>
        <div style={{display:"flex",flexDirection:"column",gap:10,alignItems:"flex-end"}}>
          <div style={{display:"flex",gap:8}}>
            <a
              onClick={async(e)=>{
                e.preventDefault();
                const token = getToken();
                const r = await fetch(`${API}/api/v1/contracts/${id}/download`,
                  {headers:{Authorization:`Bearer ${token}`}});
                const blob = await r.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href=url; a.download=`claustor-${id.slice(0,8)}.pdf`; a.click();
              }}
              href="#"
              style={{padding:"8px 14px",border:"1px solid #E5E7EB",borderRadius:8,fontSize:13,fontWeight:600,color:"#374151",textDecoration:"none",cursor:"pointer"}}>
              ⬇ Export PDF
            </a>
            {canAssign && (contract?.flagged_for_review ? (
              <button onClick={()=>{setShowAssign(true);loadUsers();}}
                style={{padding:"8px 18px",background:"#22C55E",color:"white",border:"none",borderRadius:8,fontSize:13,fontWeight:600,cursor:"pointer"}}>
                ✅ Assigned for review
              </button>
            ) : (
              <button onClick={()=>{setShowAssign(true);loadUsers();}}
                style={{padding:"8px 18px",background:"#0066FF",color:"white",border:"none",borderRadius:8,fontSize:13,fontWeight:600,cursor:"pointer"}}>
                📋 Assign for review
              </button>
            ))}
          </div>


        {contract.risk_score!==null && (
          <div style={{textAlign:"center",position:"relative"}}
            onMouseEnter={()=>setShowRiskTooltip(true)}
            onMouseLeave={()=>setShowRiskTooltip(false)}>
            <div style={{
              width:72,height:72,borderRadius:"50%",cursor:"pointer",
              background:contract.risk_score>=67?"#FEF2F2":contract.risk_score>=34?"#FFFBEB":"#F0FDF4",
              border:`3px solid ${contract.risk_score>=67?C.error:contract.risk_score>=34?C.warning:C.success}`,
              display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",
              fontSize:20,fontWeight:800,
              color:contract.risk_score>=67?C.error:contract.risk_score>=34?C.warning:C.success,
              boxShadow:"0 2px 8px rgba(0,0,0,0.08)",
            }}>
              {Math.round(contract.risk_score)}
              <div style={{fontSize:8,fontWeight:500,color:C.muted,marginTop:1}}>/ 100</div>
            </div>
            <div style={{fontSize:11,color:C.muted,marginTop:4,fontWeight:500}}>Risk score</div>
            {/* Health score below */}
            <div style={{fontSize:10,color:C.muted,marginTop:2}}>
              Health: <span style={{fontWeight:700,
                color:contractHealth(contract)>=70?C.success:contractHealth(contract)>=40?C.warning:C.error}}>
                {contractHealth(contract)}
              </span>
            </div>
            {/* Tooltip */}
            {showRiskTooltip && (
              <div style={{position:"absolute",right:"110%",top:0,zIndex:100,
                background:C.heading,color:"white",borderRadius:10,
                padding:"12px 16px",width:220,fontSize:12,
                boxShadow:"0 8px 24px rgba(0,0,0,0.2)"}}>
                <div style={{fontWeight:700,marginBottom:8}}>Risk Drivers</div>
                {(contract.clauses||[])
                  .filter((c:any)=>c.risk_level==="high")
                  .slice(0,3)
                  .map((c:any)=>(
                    <div key={c.id} style={{marginBottom:4,display:"flex",gap:6}}>
                      <span style={{color:"#EF4444"}}>●</span>
                      <span style={{color:"#D1D5DB"}}>{(c.title||c.clause_type).substring(0,30)}</span>
                    </div>
                  ))}
                {(contract.clauses||[]).filter((c:any)=>c.risk_level==="high").length===0 && (
                  <div style={{color:"#9CA3AF"}}>No high-risk clauses</div>
                )}
              </div>
            )}
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
          {label:"Auto renewal", value:contract.auto_renewal===null?null:contract.auto_renewal?`Yes (${contract.renewal_notice_days||"?"}d notice)`:"No", warn: contract.auto_renewal && (contract.renewal_notice_days||0)>90},
        ].filter(i=>i.value).map((item:any)=>(
          <div key={item.label} style={{background:(item as any).warn?"#FFFBEB":C.surface,
            border:`1px solid ${(item as any).warn?"#F59E0B40":C.border}`,
            borderRadius:10,padding:"12px 16px"}}>
            <div style={{fontSize:10,color:C.muted,marginBottom:4,textTransform:"uppercase",letterSpacing:"0.05em"}}>{item.label}</div>
            <div style={{fontSize:14,fontWeight:600,color:(item as any).warn?C.warning:C.heading}}>
              {(item as any).warn && <span style={{marginRight:4}}>⚠️</span>}
              {item.value}
            </div>
          </div>
        ))}
      </div>

      {/* Missing Clauses Alert */}
      {contract.missing_clauses?.length > 0 && (
        <div style={{background:"#FFFBEB",border:"1px solid #F59E0B40",borderRadius:12,
          padding:"12px 20px",marginBottom:16,display:"flex",alignItems:"flex-start",gap:12}}>
          <span style={{fontSize:18,flexShrink:0}}>⚠️</span>
          <div>
            <div style={{fontSize:13,fontWeight:700,color:C.warning,marginBottom:6}}>
              {contract.missing_clauses.length} Missing Clause{contract.missing_clauses.length>1?"s":""} Detected
            </div>
            <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
              {contract.missing_clauses.map((m:any)=>(
                <span key={m.clause_type} style={{fontSize:11,fontWeight:600,padding:"2px 8px",
                  borderRadius:20,
                  background:m.severity==="critical"?"#FEF2F2":m.severity==="high"?"#FFFBEB":"#F3F4F6",
                  color:m.severity==="critical"?"#DC2626":m.severity==="high"?"#D97706":"#6B7280"}}>
                  {m.severity==="critical"?"🚨":m.severity==="high"?"⚠️":"📌"} {m.label}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* AI Key Takeaways */}
      {contract.summary && (
        <div style={{background:C.primaryLight,border:`1px solid ${C.primary}30`,
          borderRadius:12,padding:"16px 20px",marginBottom:24}}>
          <div style={{fontSize:11,fontWeight:700,color:C.primary,marginBottom:10,
            textTransform:"uppercase",letterSpacing:"0.05em"}}>🤖 AI Key Takeaways</div>
          {/* Structured bullets from summary */}
          <div style={{display:"flex",flexDirection:"column",gap:6,marginBottom:10}}>
            {parseAISummary(contract.summary).map((b,i)=>(
              <div key={i} style={{display:"flex",gap:8,fontSize:13}}>
                <span style={{fontWeight:700,color:C.primary,minWidth:80}}>{b.label}:</span>
                <span style={{color:C.body}}>{b.value}</span>
              </div>
            ))}
          </div>
          {/* Full summary collapsed */}
          <details>
            <summary style={{fontSize:12,color:C.primary,cursor:"pointer",fontWeight:600}}>
              View full summary
            </summary>
            <p style={{fontSize:13,color:C.body,lineHeight:1.6,margin:"8px 0 0"}}>{contract.summary}</p>
          </details>
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
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
          {/* Left: Metadata */}
          <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24}}>
            <h3 style={{fontSize:14,fontWeight:700,color:C.heading,marginBottom:12}}>📋 Contract Details</h3>
            {[
              {label:"Original filename", value:contract.original_filename},
              {label:"Language",          value:contract.detected_language||contract.language||"en"},
              {label:"Total clauses",     value:String(contract.clause_count||0)},
              {label:"Missing clauses",   value:String(contract.missing_clauses?.length||0)+" detected"},
              {label:"Uploaded",          value:new Date(contract.created_at).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"})},
              {label:"Last updated",      value:new Date(contract.updated_at).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"})},
            ].map(row=>(
              <div key={row.label} style={{display:"flex",justifyContent:"space-between",
                padding:"9px 0",borderBottom:`1px solid ${C.border}`,fontSize:13}}>
                <span style={{color:C.muted}}>{row.label}</span>
                <span style={{fontWeight:600,color:C.body}}>{row.value||"—"}</span>
              </div>
            ))}

            {/* Clause Health Score */}
            <div style={{marginTop:16,padding:"12px 0",borderTop:`1px solid ${C.border}`}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:8}}>
                <span style={{fontSize:12,fontWeight:700,color:C.muted,textTransform:"uppercase"}}>
                  Contract Health
                </span>
                <span style={{fontSize:14,fontWeight:800,
                  color:contractHealth(contract)>=70?C.success:contractHealth(contract)>=40?C.warning:C.error}}>
                  {contractHealth(contract)}/100
                </span>
              </div>
              <div style={{height:8,background:C.border,borderRadius:4,overflow:"hidden"}}>
                <div style={{height:"100%",borderRadius:4,
                  width:`${contractHealth(contract)}%`,
                  background:contractHealth(contract)>=70?C.success:contractHealth(contract)>=40?C.warning:C.error,
                  transition:"width 0.5s ease"}}/>
              </div>
              <div style={{fontSize:11,color:C.muted,marginTop:4}}>
                Based on risk score, missing clauses, and playbook alignment
              </div>
            </div>
          </div>

          {/* Right: Document text preview */}
          <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}>
              <h3 style={{fontSize:14,fontWeight:700,color:C.heading,margin:0}}>📄 Document Preview</h3>
              <a onClick={async(e)=>{
                  e.preventDefault();
                  const token=getToken();
                  const r=await fetch(`${API}/api/v1/contracts/${id}/download`,
                    {headers:{Authorization:`Bearer ${token}`}});
                  if(r.ok){
                    const blob=await r.blob();
                    const url=URL.createObjectURL(blob);
                    const a=document.createElement("a");
                    a.href=url;a.download=`contract-${id.slice(0,8)}.pdf`;a.click();
                  } else { alert("Original file not found on server"); }
                }} href="#"
                style={{fontSize:12,color:C.primary,fontWeight:600,
                  textDecoration:"none",cursor:"pointer"}}>
                ⬇ Download Original
              </a>
            </div>
            {!pdfUrl && !pdfLoading && (
              <button onClick={loadPdf}
                style={{width:"100%",padding:"40px 20px",border:`2px dashed ${C.border}`,
                  borderRadius:10,background:C.bg,cursor:"pointer",
                  fontSize:13,color:C.primary,fontWeight:600}}>
                📄 Click to load PDF preview
              </button>
            )}
            {pdfLoading && (
              <div style={{textAlign:"center",padding:40,color:C.muted}}>Loading PDF...</div>
            )}
            {pdfUrl && (
              <iframe src={pdfUrl}
                style={{width:"100%",height:400,border:`1px solid ${C.border}`,
                  borderRadius:8,background:C.bg}}
                title="Contract PDF Preview"/>
            )}
          </div>
        </div>
      )}

      {/* Tab: Clauses */}
      {tab==="clauses" && (
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          {contract.clauses?.length===0 ? (
            <div style={{textAlign:"center",padding:60,color:C.muted}}>No clauses extracted yet</div>
          ) : contract.clauses?.map(clause=>(
            <div key={clause.id} id={"clause-"+clause.clause_type} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:20}}>
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
                <div style={{marginTop:8,padding:"8px 12px",background:C.bg,borderRadius:8,fontSize:13,color:C.muted}}>
                  ⚠️ {clause.risk_reason}
                </div>
              )}

              {/* Phase 2: Playbook match + deviation */}
              {(clause.playbook_match!=null || clause.deviation_from_std) && (
                <div style={{marginTop:8,display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
                  {clause.playbook_match!=null && (
                    <span style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,
                      background:(clause.playbook_match||0)>0.6?"#F0FDF4":(clause.playbook_match||0)>0.3?"#FFFBEB":"#FEF2F2",
                      color:(clause.playbook_match||0)>0.6?"#16A34A":(clause.playbook_match||0)>0.3?"#D97706":"#DC2626"}}>
                      📋 Playbook {Math.round((clause.playbook_match||0)*100)}%
                    </span>
                  )}
                  {clause.adjusted_risk && clause.adjusted_risk !== clause.risk_score && (
                    <span style={{fontSize:11,padding:"2px 8px",borderRadius:20,
                      background:"#F5F3FF",color:"#7C3AED",fontWeight:600}}>
                      ⚖️ Adj. risk: {Math.round(clause.adjusted_risk)}
                    </span>
                  )}
                  {clause.deviation_from_std && (
                    <span style={{fontSize:11,color:C.muted,fontStyle:"italic"}}>
                      {clause.deviation_from_std}
                    </span>
                  )}
                </div>
              )}

              {/* Phase 3: Related clauses */}
              {clause.related_clauses?.length > 0 && (
                <div style={{marginTop:6,display:"flex",gap:6,alignItems:"center",flexWrap:"wrap"}}>
                  <span style={{fontSize:11,color:C.muted,fontWeight:500}}>Related:</span>
                  {clause.related_clauses.map((r:string)=>(
                    <span key={r}
                      onClick={()=>{
                        const el = document.getElementById("clause-"+r);
                        if(el) el.scrollIntoView({behavior:"smooth",block:"center"});
                      }}
                      style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,
                        background:C.primaryLight,color:C.primary,cursor:"pointer",
                        border:`1px solid ${C.primary}30`}}>
                      → {r.replace(/_/g," ")}
                    </span>
                  ))}
                </div>
              )}

              {/* Phase 3: Cross references */}
              {clause.cross_references?.length > 0 && (
                <div style={{marginTop:4,fontSize:11,color:C.muted}}>
                  📎 References: {clause.cross_references.join(", ")}
                </div>
              )}

              {/* Show review decision for this clause */}
              {clauseFlags[clause.id] && (
                <div style={{marginTop:10,padding:"8px 12px",borderRadius:8,display:"flex",gap:8,alignItems:"center",
                  background: clauseFlags[clause.id].action==="accept"?"#F0FDF4":
                              clauseFlags[clause.id].action==="flag"?"#FEF2F2":"#FFFBEB",
                  border:`1px solid ${clauseFlags[clause.id].action==="accept"?"#22C55E30":
                                     clauseFlags[clause.id].action==="flag"?"#EF444430":"#F59E0B30"}`}}>
                  <span style={{fontSize:14}}>
                    {clauseFlags[clause.id].action==="accept"?"✅":
                     clauseFlags[clause.id].action==="flag"?"🚩":"💬"}
                  </span>
                  <div>
                    <span style={{fontSize:12,fontWeight:700,
                      color:clauseFlags[clause.id].action==="accept"?"#16A34A":
                           clauseFlags[clause.id].action==="flag"?"#DC2626":"#D97706"}}>
                      {clauseFlags[clause.id].action==="accept"?"Accepted by reviewer":
                       clauseFlags[clause.id].action==="flag"?"Flagged by reviewer":"Reviewer note"}
                    </span>
                    {clauseFlags[clause.id].comment && (
                      <div style={{fontSize:12,color:"#374151",marginTop:2}}>
                        {clauseFlags[clause.id].comment}
                      </div>
                    )}
                    <div style={{fontSize:11,color:"#9CA3AF",marginTop:2}}>
                      {clauseFlags[clause.id].reviewer}
                    </div>
                  </div>
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
        <div style={{display:"flex",flexDirection:"column",height:560,
          background:"rgba(255,255,255,0.85)",backdropFilter:"blur(12px)",
          border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden",
          boxShadow:"0 4px 20px rgba(0,0,0,0.06)"}}>

          {/* Review status banner */}
          {contract?.review_status && ["rejected","revision_needed"].includes(contract.review_status) && (
            <div style={{padding:"10px 16px",
              background:contract.review_status==="rejected"?"#FEF2F2":"#FFFBEB",
              borderBottom:`2px solid ${contract.review_status==="rejected"?"#EF4444":"#F59E0B"}`,
              display:"flex",alignItems:"center",gap:10,flexShrink:0}}>
              <span style={{fontSize:18}}>{contract.review_status==="rejected"?"❌":"🔄"}</span>
              <div>
                <span style={{fontSize:13,fontWeight:800,
                  color:contract.review_status==="rejected"?"#DC2626":"#D97706"}}>
                  {contract.review_status==="rejected"
                    ?"CONTRACT REJECTED — Do not execute"
                    :"REVISION REQUIRED — Address issues before signing"}
                </span>
                {contract.review_notes && (
                  <span style={{fontSize:12,color:"#374151",marginLeft:8}}>· {contract.review_notes}</span>
                )}
              </div>
            </div>
          )}

          {/* Messages */}
          <div style={{flex:1,overflowY:"auto",padding:20,display:"flex",flexDirection:"column",gap:16}}>
            {chatMessages.length===0 && (
              <div style={{textAlign:"center",paddingTop:30,color:C.muted}}>
                <div style={{width:52,height:52,borderRadius:14,margin:"0 auto 12px",
                  background:"white",border:"1.5px solid rgba(0,102,255,0.2)",
                  display:"flex",alignItems:"center",justifyContent:"center",
                  boxShadow:"0 4px 12px rgba(91,75,255,0.1)"}}>
                  <ClauStorMark size={30}/>
                </div>
                <p style={{fontSize:14,marginBottom:20,color:C.muted}}>Ask anything about this contract</p>
                <div style={{display:"flex",flexWrap:"wrap",gap:8,justifyContent:"center"}}>
                  {["What is the liability cap?","What are the payment terms?",
                    "When does this expire?","Is there auto-renewal?",
                    "What are the key risks?","Who are the parties?"].map(q=>(
                    <button key={q} onClick={()=>sendChat(q)}
                      style={{padding:"6px 14px",
                        border:"1px solid rgba(91,75,255,0.2)",borderRadius:20,
                        background:"rgba(91,75,255,0.05)",backdropFilter:"blur(8px)",
                        color:C.primary,fontSize:12,cursor:"pointer",fontWeight:500,
                        transition:"all 0.15s"}}
                      onMouseEnter={e=>{(e.currentTarget as HTMLElement).style.background="rgba(91,75,255,0.12)";}}
                      onMouseLeave={e=>{(e.currentTarget as HTMLElement).style.background="rgba(91,75,255,0.05)";}}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {chatMessages.map((msg:any,i:number)=>(
              <div key={i} style={{display:"flex",
                justifyContent:msg.role==="user"?"flex-end":"flex-start",
                gap:10,alignItems:"flex-start",
                animation:"msgIn 0.25s ease-out"}}>
                {msg.role==="assistant" && (
                  <div style={{width:26,height:26,borderRadius:8,flexShrink:0,
                    background:"white",border:"1.5px solid rgba(91,75,255,0.2)",
                    display:"flex",alignItems:"center",justifyContent:"center",marginTop:2,
                    boxShadow:"0 2px 6px rgba(91,75,255,0.1)"}}>
                    <ClauStorMark size={15}/>
                  </div>
                )}
                <div style={{maxWidth:"80%"}}>
                  <div style={{padding:"10px 14px",
                    borderRadius:msg.role==="user"?"14px 14px 4px 14px":"4px 14px 14px 14px",
                    background:msg.role==="user"
                      ? "linear-gradient(135deg,#0066FF,#0052CC)"
                      : "rgba(255,255,255,0.9)",
                    backdropFilter:msg.role==="assistant"?"blur(8px)":"none",
                    color:msg.role==="user"?"white":C.body,
                    border:msg.role==="assistant"?`1px solid rgba(0,0,0,0.06)`:"none",
                    fontSize:13,lineHeight:1.7,
                    boxShadow:msg.role==="user"
                      ? "0 4px 12px rgba(91,75,255,0.25)"
                      : "0 2px 6px rgba(0,0,0,0.05)"}}>
                    {msg.role==="assistant"
                      ? (msg.content
                          ? <MarkdownText content={msg.content} color={C.body}/>
                          : <TypingDots/>)
                      : msg.content}
                  </div>
                  {msg.db_sourced && (
                    <div style={{fontSize:10,color:"#16A34A",marginTop:3,display:"flex",alignItems:"center",gap:3}}>
                      <span>🗄️</span><span style={{fontWeight:600}}>Live Database</span>
                    </div>
                  )}
                  {msg.role==="assistant" && msg.groundedness!==undefined && !msg.db_sourced && msg.groundedness>0 && (
                    <div style={{fontSize:10,marginTop:3,display:"inline-flex",alignItems:"center",gap:3,
                      padding:"2px 7px",borderRadius:20,
                      background:msg.groundedness>=0.8?"rgba(34,197,94,0.08)":"rgba(245,158,11,0.08)",
                      color:msg.groundedness>=0.8?"#22C55E":"#F59E0B",
                      border:`1px solid ${msg.groundedness>=0.8?"#22C55E30":"#F59E0B30"}`}}>
                      ✓ Verified {Math.round(msg.groundedness*100)}%
                    </div>
                  )}
                  {msg.citations && msg.citations.length>0 && (
                    <div style={{marginTop:5,display:"flex",flexWrap:"wrap",gap:4}}>
                      {msg.citations.slice(0,4).map((cite:any,ci:number)=>(
                        <span key={ci} style={{fontSize:10,padding:"2px 7px",borderRadius:10,
                          background:"rgba(91,75,255,0.08)",backdropFilter:"blur(4px)",
                          color:C.primary,fontWeight:600,
                          border:"1px solid rgba(91,75,255,0.15)"}}>
                          [{cite.index||cite.citation_number||ci+1}] {(cite.clause_type||cite.source||"").replace(/_/g," ")}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <div style={{padding:"10px 14px",borderTop:`1px solid ${C.border}`,
            background:"rgba(255,255,255,0.8)",backdropFilter:"blur(8px)",flexShrink:0}}>
            <div style={{display:"flex",gap:8,alignItems:"flex-end"}}>
              <div style={{flex:1,border:`1.5px solid ${chatLoading?C.primary:C.border}`,
                borderRadius:12,background:"rgba(255,255,255,0.8)",overflow:"hidden",
                transition:"all 0.15s",
                boxShadow:chatLoading?`0 0 0 3px rgba(91,75,255,0.1)`:"none"}}>
                <textarea value={chatInput} onChange={e=>setChatInput(e.target.value)}
                  onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendChat();}}}
                  placeholder="Ask about this contract..." disabled={chatLoading} rows={1}
                  style={{width:"100%",padding:"9px 13px",border:"none",fontSize:13,
                    color:C.heading,background:"transparent",resize:"none",outline:"none",
                    fontFamily:"inherit",lineHeight:1.5,maxHeight:100,overflowY:"auto",
                    boxSizing:"border-box"}}
                  onInput={e=>{const t=e.currentTarget;t.style.height="auto";t.style.height=Math.min(t.scrollHeight,100)+"px";}}/>
              </div>
              <button onClick={()=>sendChat()}
                disabled={chatLoading||!chatInput.trim()}
                style={{width:38,height:38,borderRadius:10,border:"none",
                  background:chatLoading?"rgba(239,68,68,0.1)":chatInput.trim()
                    ? "linear-gradient(135deg,#0066FF,#0052CC)"
                    : "rgba(226,232,240,0.8)",
                  backdropFilter:"blur(8px)",
                  color:chatLoading?"#EF4444":chatInput.trim()?"white":"#94A3B8",
                  cursor:chatLoading||!chatInput.trim()?"not-allowed":"pointer",
                  display:"flex",alignItems:"center",justifyContent:"center",
                  transition:"all 0.2s",
                  boxShadow:chatInput.trim()&&!chatLoading?"0 4px 12px rgba(91,75,255,0.3)":"none"}}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </button>
            </div>
            <p style={{fontSize:10,color:C.muted,textAlign:"center",marginTop:5}}>
              AI-powered · Scoped to this contract · Not legal advice
            </p>
          </div>
        </div>
      )}
      <style>{`
        @keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
        @keyframes typingDot{0%,100%{opacity:0.4;transform:translateY(0)}50%{opacity:1;transform:translateY(-3px)}}
        @keyframes msgIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
      `}</style>

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
                      style={{flex:1,padding:"8px",border:`2px solid ${priority===p?"#0066FF":C.border}`,
                        borderRadius:8,background:priority===p?"#E6F0FF":"none",
                        color:priority===p?"#0066FF":C.muted,fontSize:12,fontWeight:600,cursor:"pointer",textTransform:"capitalize"}}>
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
                  background:!reviewerId||assigning?"#D1D5DB":"#0066FF",
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
