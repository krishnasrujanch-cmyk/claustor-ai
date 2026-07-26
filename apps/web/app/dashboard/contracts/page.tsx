"use client";
import { Pagination } from "@/components/shared/Pagination";
import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { getToken } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { can } from "@/lib/permissions";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF", primaryDark:"#4338CA",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  error:"#EF4444", errorLight:"#FEF2F2",
  success:"#22C55E", successLight:"#F0FDF4",
  warning:"#F59E0B", warningLight:"#FFFBEB",
};

const RISK_META: Record<string,{bg:string,text:string,dot:string}> = {
  high:   {bg:"#FEF2F2",text:"#DC2626",dot:"#EF4444"},
  medium: {bg:"#FFFBEB",text:"#D97706",dot:"#F59E0B"},
  low:    {bg:"#F0FDF4",text:"#16A34A",dot:"#22C55E"},
};
const REVIEW_META: Record<string,{bg:string,text:string,label:string}> = {
  approved:        {bg:"#F0FDF4",text:"#16A34A",label:"✅ Approved"},
  rejected:        {bg:"#FEF2F2",text:"#DC2626",label:"❌ Rejected"},
  revision_needed: {bg:"#FFFBEB",text:"#D97706",label:"🔄 Revision"},
};

// ─── Risk Badge ───────────────────────────────────────────────────────────────
function RiskBadge({level}:{level:string}) {
  const m = RISK_META[level]||{bg:"#F3F4F6",text:"#6B7280",dot:"#9CA3AF"};
  return (
    <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,
      background:m.bg,color:m.text,textTransform:"uppercase",letterSpacing:"0.04em",
      whiteSpace:"nowrap"}}>
      {level}
    </span>
  );
}

// ─── Review Badge (subtle when approved + high-risk conflict handled by parent) ─
function ReviewBadge({status,riskLevel}:{status:string,riskLevel?:string}) {
  const m = REVIEW_META[status];
  if (!m) return <span style={{color:C.muted,fontSize:12}}>—</span>;
  // Neutral styling when approved but high risk
  const isConflict = status==="approved" && riskLevel==="high";
  return (
    <span style={{fontSize:11,fontWeight:600,padding:"3px 10px",borderRadius:20,
      background:isConflict?"#F3F4F6":m.bg,
      color:isConflict?C.muted:m.text,
      whiteSpace:"nowrap"}}
      title={isConflict?"Approved but high risk — review recommended":""}>
      {isConflict?"✅ Approved*":m.label}
    </span>
  );
}

interface UploadState {
  _id:string; file:File; uploadPct:number; contractId:string|null;
  status:string; step:string; analysisPct:number; error:string|null;
  done:boolean; parentId?:string|null;
}

// ─── Action Menu ──────────────────────────────────────────────────────────────
function ActionMenu({contract, role, onReprocess, onDelete, onUploadVersion}:{
  contract:any; role:string;
  onReprocess:(id:string,title:string)=>void;
  onDelete:(id:string,title:string)=>void;
  onUploadVersion:(id:string,file:File)=>void;
}) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(()=>{
    const handler = (e:MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return ()=>document.removeEventListener("mousedown", handler);
  },[]);

  const items = [
    {label:"View contract", icon:"🔍", always:true,
      action:()=>{ router.push(`/dashboard/contracts/${contract.id}`); setOpen(false); }},
    {label:"Upload new version", icon:"📎", show:can(role,"contract.upload_version"),
      action:()=>{ fileRef.current?.click(); setOpen(false); }},
    {label:"Reprocess", icon:"↺", show:can(role,"contract.reprocess") && ["analyzed","failed"].includes(contract.status),
      action:()=>{ onReprocess(contract.id,contract.title); setOpen(false); }},
    {label:"Delete", icon:"🗑", show:can(role,"contract.delete"), danger:true,
      action:()=>{ onDelete(contract.id,contract.title); setOpen(false); }},
  ].filter(i=>i.always||i.show);

  return (
    <div ref={ref} style={{position:"relative"}}>
      <button onClick={()=>setOpen(!open)}
        style={{padding:"5px 8px",border:`1px solid ${C.border}`,borderRadius:8,
          background:open?C.primaryLight:C.surface,cursor:"pointer",
          fontSize:16,color:C.muted,lineHeight:1}}>
        ⋮
      </button>
      {open && (
        <div style={{position:"absolute",right:0,top:"110%",zIndex:100,
          background:C.surface,border:`1px solid ${C.border}`,borderRadius:10,
          boxShadow:"0 8px 24px rgba(0,0,0,0.12)",padding:4,minWidth:180}}>
          {items.map(item=>(
            <button key={item.label} onClick={item.action}
              style={{display:"flex",alignItems:"center",gap:8,width:"100%",
                padding:"8px 12px",border:"none",background:"none",
                cursor:"pointer",borderRadius:6,textAlign:"left",
                fontSize:13,color:(item as any).danger?C.error:C.body,
                fontWeight:500}}>
              <span>{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>
      )}
      <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.xlsx,.xml"
        style={{display:"none"}}
        onChange={e=>{
          const f=e.target.files?.[0];
          if(f) onUploadVersion(contract.id,f);
        }}/>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ContractsPage() {
  const router = useRouter();
  const { user: currentUser } = useAuthStore();
  const role = currentUser?.role || "";

  const [contracts, setContracts] = useState<any[]>([]);
  const [total, setTotal]         = useState(0);
  const [page, setPage]           = useState(1);
  const [search, setSearch]       = useState("");
  const [risk, setRisk]           = useState("");
  const [status, setStatus]       = useState("");
  const [quickTab, setQuickTab]   = useState("all");
  const [loading, setLoading]     = useState(true);
  const [uploads, setUploads]     = useState<UploadState[]>([]);
  const [toast, setToast]         = useState("");
  const [expanded, setExpanded]   = useState<Set<string>>(new Set());
  const fileRef = useRef<HTMLInputElement>(null);
  const PAGE_SIZE = 20;

  // Quick tab counts
  const tabCounts = useMemo(()=>({
    all:    total,
    high:   contracts.filter(c=>c.risk_level==="high").length,
    medium: contracts.filter(c=>c.risk_level==="medium").length,
    low:    contracts.filter(c=>c.risk_level==="low").length,
    pending:contracts.filter(c=>!c.review_status).length,
  }),[contracts,total]);

  const load = useCallback(async () => {
    setLoading(true);
    const token = getToken();
    const params = new URLSearchParams({
      page:String(page), page_size:String(PAGE_SIZE),
      ...(search && {search}),
      ...(risk && {risk_level:risk}),
      ...(status && {status}),
    });
    try {
      const r = await fetch(`${API}/api/v1/contracts/grouped?${params}`,
        {headers:{Authorization:`Bearer ${token}`}});
      const d = await r.json();
      setContracts(d.contracts||[]);
      setTotal(d.total||0);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  }, [page, search, risk, status]);

  useEffect(()=>{ load(); },[load]);

  // Apply quick tab filter locally
  const displayContracts = useMemo(()=>{
    if (quickTab==="all") return contracts;
    if (quickTab==="pending") return contracts.filter(c=>!c.review_status);
    return contracts.filter(c=>c.risk_level===quickTab);
  },[contracts,quickTab]);

  const handleUpload = async (file:File, parentId?:string|null) => {
    const token = getToken();
    const uploadId = Date.now().toString();
    setUploads(prev=>[...prev,{
      _id:uploadId,file,uploadPct:0,contractId:null,
      status:"uploading",step:"Uploading file...",
      analysisPct:0,error:null,done:false,parentId:parentId||null,
    }]);
    const update = (patch:Partial<UploadState>) =>
      setUploads(prev=>prev.map(u=>u._id===uploadId?{...u,...patch}:u));

    try {
      const contractId = await new Promise<string>((resolve,reject)=>{
        const xhr = new XMLHttpRequest();
        const form = new FormData();
        form.append("file",file);
        if (parentId) {
          form.append("parent_contract_id",parentId);
          form.append("version_note","New version");
        }
        xhr.upload.onprogress = e=>{
          if(e.lengthComputable) update({uploadPct:Math.round(e.loaded/e.total*100)});
        };
        xhr.onload = ()=>{
          if(xhr.status===202||xhr.status===200)
            resolve(JSON.parse(xhr.responseText).contract_id);
          else reject(new Error(JSON.parse(xhr.responseText).detail||"Upload failed"));
        };
        xhr.onerror = ()=>reject(new Error("Network error"));
        xhr.open("POST",`${API}/api/v1/contracts/`);
        xhr.setRequestHeader("Authorization",`Bearer ${token}`);
        xhr.send(form);
      });

      update({contractId,uploadPct:100,status:"queued",step:"Queued for analysis..."});
      const STEP_LABELS:Record<string,string> = {
        queued:"Queued for analysis...",parsing:"Parsing document...",
        extracting:"Extracting clauses with AI...",scoring:"Scoring risk levels...",
        indexing:"Indexing into vector store...",analyzed:"✅ Analysis complete!",
      };
      const STEP_PCT:Record<string,number> = {
        queued:0,parsing:20,extracting:45,scoring:70,indexing:90,analyzed:100
      };
      await new Promise<void>((resolve,reject)=>{
        const poll = setInterval(async()=>{
          try {
            const r = await fetch(`${API}/api/v1/contracts/${contractId}/status`,
              {headers:{Authorization:`Bearer ${token}`}});
            const d = await r.json();
            const step = d.status||"queued";
            update({status:step,step:STEP_LABELS[step]||step,
              analysisPct:d.progress_pct??STEP_PCT[step]??0});
            if(step==="analyzed"){clearInterval(poll);update({done:true,analysisPct:100});load();resolve();}
            else if(step==="failed"){clearInterval(poll);update({error:d.error||"Failed"});reject(new Error(d.error));}
          } catch(e){clearInterval(poll);reject(e);}
        },2000);
      });
    } catch(e:any){update({error:e.message,status:"failed"});}
  };

  const deleteContract = async (id:string,title:string) => {
    if(!confirm(`Delete "${title}"? This cannot be undone.`)) return;
    const token = getToken();
    await fetch(`${API}/api/v1/contracts/${id}`,
      {method:"DELETE",headers:{Authorization:`Bearer ${token}`}});
    setContracts(prev=>prev.filter(c=>c.id!==id));
    setTotal(prev=>prev-1);
  };

  const reprocess = async (id:string,title:string) => {
    const token = getToken();
    const r = await fetch(`${API}/api/v1/contracts/${id}/reprocess`,
      {method:"POST",headers:{Authorization:`Bearer ${token}`}});
    if(r.ok){
      setContracts(prev=>prev.map(c=>c.id===id?{...c,status:"queued"}:c));
      setToast(`⏳ "${title}" queued for reprocessing`);
      setTimeout(()=>setToast(""),5000);
    } else alert("Reprocess failed");
  };

  const toggleExpand = (id:string) =>
    setExpanded(prev=>{const s=new Set(prev);s.has(id)?s.delete(id):s.add(id);return s;});

  const STEPS = ["queued","parsing","extracting","scoring","indexing","analyzed"];

  return (
    <div style={{padding:"28px 32px",maxWidth:1400,margin:"0 auto"}}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div style={{display:"flex",justifyContent:"space-between",
        alignItems:"center",marginBottom:20}}>
        <div>
          <h1 style={{fontSize:22,fontWeight:800,color:C.heading,marginBottom:2}}>
            Contracts
          </h1>
          <p style={{fontSize:13,color:C.muted}}>{total} contract families</p>
        </div>
        {can(role,"contract.upload") && (
          <>
            <button onClick={()=>fileRef.current?.click()}
              style={{background:C.primary,color:"white",border:"none",
                borderRadius:10,padding:"10px 20px",fontSize:13,fontWeight:600,
                cursor:"pointer",display:"flex",alignItems:"center",gap:6,
                boxShadow:"0 2px 8px rgba(91,75,255,0.3)"}}>
              ⬆ Upload contract
            </button>
            <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.xlsx,.xls,.xml"
              style={{display:"none"}}
              onChange={e=>e.target.files?.[0]&&handleUpload(e.target.files[0])}/>
          </>
        )}
      </div>

      {/* ── Upload Progress ─────────────────────────────────────────────── */}
      {uploads.filter(u=>!u.done).map(u=>(
        <div key={u._id} style={{background:C.surface,
          border:`1.5px solid ${u.error?C.error:C.primary}`,
          borderRadius:12,padding:20,marginBottom:16,
          boxShadow:"0 2px 8px rgba(0,0,0,0.06)"}}>
          <div style={{display:"flex",justifyContent:"space-between",
            alignItems:"center",marginBottom:12}}>
            <div>
              <div style={{fontSize:14,fontWeight:700,color:C.heading}}>
                {u.file.name}
                {u.parentId&&<span style={{fontSize:11,color:C.primary,marginLeft:8,
                  background:C.primaryLight,padding:"1px 6px",borderRadius:20}}>
                  new version
                </span>}
              </div>
              <div style={{fontSize:12,color:u.error?C.error:C.primary,marginTop:2}}>
                {u.error||u.step}
              </div>
            </div>
            <div style={{fontSize:13,fontWeight:700,color:u.error?C.error:C.primary}}>
              {u.error?"Failed":u.status==="uploading"?`${u.uploadPct}%`:`${u.analysisPct}%`}
            </div>
          </div>
          {u.status==="uploading"&&(
            <div style={{height:6,background:C.border,borderRadius:3,overflow:"hidden"}}>
              <div style={{height:"100%",width:`${u.uploadPct}%`,
                background:C.primary,borderRadius:3,transition:"width 0.3s"}}/>
            </div>
          )}
          {u.status!=="uploading"&&!u.error&&(
            <div>
              <div style={{display:"flex",gap:4,marginBottom:8}}>
                {STEPS.map(step=>{
                  const done=STEPS.indexOf(u.status)>=STEPS.indexOf(step);
                  return(
                    <div key={step} style={{flex:1,textAlign:"center"}}>
                      <div style={{height:4,borderRadius:2,
                        background:done?C.primary:C.border,marginBottom:4,
                        transition:"background 0.3s"}}/>
                      <div style={{fontSize:9,color:done?C.primary:C.muted,
                        fontWeight:done?600:400,textTransform:"capitalize"}}>
                        {step}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div style={{height:8,background:C.border,borderRadius:4,overflow:"hidden"}}>
                <div style={{height:"100%",width:`${u.analysisPct}%`,
                  background:`linear-gradient(90deg,${C.primary},#06B6D4)`,
                  borderRadius:4,transition:"width 0.5s ease"}}/>
              </div>
            </div>
          )}
        </div>
      ))}

      {/* ── Search + Filters ────────────────────────────────────────────── */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,
        borderRadius:12,padding:"14px 16px",marginBottom:16,
        boxShadow:"0 1px 3px rgba(0,0,0,0.04)"}}>
        <div style={{display:"flex",gap:10,marginBottom:12,flexWrap:"wrap"}}>
          <div style={{flex:1,minWidth:220,position:"relative"}}>
            <span style={{position:"absolute",left:10,top:"50%",
              transform:"translateY(-50%)",color:C.muted,fontSize:14}}>🔍</span>
            <input value={search}
              onChange={e=>{setSearch(e.target.value);setPage(1);setQuickTab("all");}}
              placeholder="Search contracts, counterparties..."
              style={{width:"100%",padding:"8px 12px 8px 32px",
                border:`1.5px solid ${C.border}`,borderRadius:8,
                fontSize:13,outline:"none",boxSizing:"border-box"}}/>
          </div>
          <select value={risk} onChange={e=>{setRisk(e.target.value);setPage(1);}}
            style={{padding:"8px 12px",border:`1.5px solid ${C.border}`,
              borderRadius:8,fontSize:13,background:C.surface,cursor:"pointer"}}>
            <option value="">All Risk Levels</option>
            <option value="high">🔴 High Risk</option>
            <option value="medium">🟡 Medium Risk</option>
            <option value="low">🟢 Low Risk</option>
          </select>
          <select value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}}
            style={{padding:"8px 12px",border:`1.5px solid ${C.border}`,
              borderRadius:8,fontSize:13,background:C.surface,cursor:"pointer"}}>
            <option value="">All Statuses</option>
            <option value="analyzed">Analyzed</option>
            <option value="queued">Processing</option>
            <option value="failed">Failed</option>
          </select>
          {(search||risk||status) && (
            <button onClick={()=>{setSearch("");setRisk("");setStatus("");setPage(1);}}
              style={{padding:"8px 14px",background:C.errorLight,border:"none",
                borderRadius:8,fontSize:12,color:C.error,cursor:"pointer",fontWeight:600}}>
              ✕ Clear
            </button>
          )}
        </div>

        {/* Quick Tabs */}
        <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
          {[
            {key:"all",    label:`All`,           count:total},
            {key:"high",   label:`🔴 High Risk`,  count:tabCounts.high},
            {key:"medium", label:`🟡 Medium`,      count:tabCounts.medium},
            {key:"low",    label:`🟢 Low Risk`,   count:tabCounts.low},
            {key:"pending",label:`⏳ Pending Review`,count:tabCounts.pending},
          ].map(tab=>(
            <button key={tab.key}
              onClick={()=>{setQuickTab(tab.key);}}
              style={{padding:"5px 14px",borderRadius:20,border:"none",cursor:"pointer",
                fontSize:12,fontWeight:600,transition:"all 0.15s",
                background:quickTab===tab.key?C.primary:C.bg,
                color:quickTab===tab.key?"white":C.muted}}>
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>
      </div>

      {/* ── Table ───────────────────────────────────────────────────────── */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,
        borderRadius:12,overflow:"hidden",
        boxShadow:"0 1px 3px rgba(0,0,0,0.06)"}}>

        {loading ? (
          <div style={{padding:60,textAlign:"center",color:C.muted}}>
            <div style={{fontSize:24,marginBottom:8}}>⏳</div>
            Loading contracts...
          </div>
        ) : displayContracts.length===0 ? (
          <div style={{padding:60,textAlign:"center"}}>
            <div style={{fontSize:48,marginBottom:12}}>📄</div>
            <div style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:6}}>
              No contracts found
            </div>
            <div style={{fontSize:13,color:C.muted}}>
              {search||risk||status?"Try adjusting your filters":"Upload your first contract to get started"}
            </div>
          </div>
        ) : (
          <>
            {/* Table Header */}
            <div style={{display:"grid",
              gridTemplateColumns:"minmax(180px,2fr) minmax(120px,1.5fr) 150px 110px 145px 90px",
              padding:"10px 20px",background:"#F8F9FF",
              borderBottom:`2px solid ${C.border}`}}>
              {["CONTRACT & TYPE","COUNTERPARTY","VALUE","RISK","REVIEW STATUS","ACTION"].map((h,i)=>(
                <div key={i} style={{fontSize:11,fontWeight:700,color:C.muted,
                  textTransform:"uppercase",letterSpacing:"0.06em",
                  textAlign:"left"}}>
                  {h}
                </div>
              ))}
            </div>

            {displayContracts.map(c=>{
              const isExpanded = expanded.has(c.id);
              const hasVersions = c.version_count > 1;
              const riskMeta = RISK_META[c.risk_level]||{dot:"#D1D5DB"};

              return (
                <div key={c.id}
                  style={{borderBottom:`1px solid ${C.border}`}}>

                  {/* Main Row */}
                  <div style={{display:"grid",
                    gridTemplateColumns:"minmax(180px,2fr) minmax(120px,1.5fr) 150px 110px 145px 90px",
                    padding:"14px 20px",alignItems:"center",
                    background:isExpanded?C.primaryLight:C.surface,
                    transition:"background 0.15s"}}
                    onMouseEnter={e=>{if(!isExpanded)e.currentTarget.style.background=C.bg;}}
                    onMouseLeave={e=>{if(!isExpanded)e.currentTarget.style.background=C.surface;}}>

                    {/* Contract & Type */}
                    <div style={{display:"flex",alignItems:"center",gap:10}}>
                      {/* Risk dot */}
                      <div style={{width:8,height:8,borderRadius:"50%",
                        background:riskMeta.dot,flexShrink:0}}/>
                      <div>
                        <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:2}}>
                          <span onClick={()=>router.push(`/dashboard/contracts/${c.id}`)}
                            style={{fontSize:14,fontWeight:700,color:C.heading,
                              cursor:"pointer",lineHeight:1.3}}>
                            {c.title||"Untitled"}
                          </span>
                          {/* Attachment / version count badge next to title */}
                          {hasVersions && (
                            <span title={`${c.version_count} versions`}
                              style={{fontSize:10,fontWeight:700,padding:"1px 6px",
                                borderRadius:20,background:C.primaryLight,
                                color:C.primary,cursor:"pointer"}}
                              onClick={()=>toggleExpand(c.id)}>
                              📎 {c.version_count}v
                            </span>
                          )}
                          {c.status!=="analyzed" && (
                            <span style={{fontSize:10,padding:"1px 6px",borderRadius:20,
                              background:"#F3F4F6",color:C.muted}}>{c.status}</span>
                          )}
                        </div>
                        <div style={{fontSize:11,color:C.muted,display:"flex",
                          alignItems:"center",gap:6}}>
                          <span>{c.contract_type||"Contract"}</span>
                          {hasVersions && (
                            <span style={{color:C.primary,cursor:"pointer",fontWeight:600}}
                              onClick={()=>toggleExpand(c.id)}>
                              {isExpanded?"▲ hide":"▼ versions"}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Counterparty */}
                    <div style={{fontSize:13,color:C.body,
                      overflow:"hidden",textOverflow:"ellipsis",
                      whiteSpace:"nowrap",paddingRight:8}}>
                      {c.counterparty||"—"}
                    </div>

                    {/* Value — right aligned */}
                    <div style={{fontSize:13,fontWeight:600,color:C.heading,
                      textAlign:"left",fontVariantNumeric:"tabular-nums"}}>
                      {c.contract_value
                        ? `${c.contract_currency||"₹"}${Number(c.contract_value).toLocaleString("en-IN")}`
                        : <span style={{color:C.muted,fontWeight:400}}>—</span>}
                    </div>

                    {/* Risk */}
                    <div>
                      {c.risk_level
                        ? <RiskBadge level={c.risk_level}/>
                        : <span style={{color:C.muted,fontSize:13}}>—</span>}
                    </div>

                    {/* Review Status */}
                    <div>
                      {c.review_status
                        ? <ReviewBadge status={c.review_status} riskLevel={c.risk_level}/>
                        : <span style={{color:C.muted,fontSize:12}}>—</span>}
                    </div>

                    {/* Action — Primary + Menu */}
                    <div style={{display:"flex",alignItems:"center",gap:6}}>
                      <button
                        onClick={()=>router.push(`/dashboard/contracts/${c.id}`)}
                        style={{padding:"5px 12px",background:C.primary,color:"white",
                          border:"none",borderRadius:7,fontSize:12,fontWeight:600,
                          cursor:"pointer",whiteSpace:"nowrap"}}>
                        View
                      </button>
                      <ActionMenu
                        contract={c} role={role}
                        onReprocess={reprocess}
                        onDelete={deleteContract}
                        onUploadVersion={(id,f)=>handleUpload(f,id)}/>
                    </div>
                  </div>

                  {/* Version History Expanded */}
                  {isExpanded && hasVersions && (
                    <div style={{background:"#F5F6FF",
                      borderTop:`1px solid ${C.primary}20`,
                      padding:"12px 20px 12px 52px"}}>
                      <div style={{fontSize:11,fontWeight:700,color:C.muted,
                        textTransform:"uppercase",letterSpacing:"0.05em",
                        marginBottom:8}}>Version History</div>
                      {c.versions.map((v:any)=>{
                        const vm = RISK_META[v.risk_level]||{dot:"#D1D5DB"};
                        const rm = v.review_status?REVIEW_META[v.review_status]:null;
                        return (
                          <div key={v.id}
                            onClick={()=>router.push(`/dashboard/contracts/${v.id}`)}
                            style={{display:"flex",alignItems:"center",gap:12,
                              padding:"8px 14px",marginBottom:4,borderRadius:8,
                              cursor:"pointer",
                              background:v.is_latest?"white":C.bg,
                              border:`1px solid ${v.is_latest?C.primary:C.border}`,
                              transition:"all 0.15s"}}
                            onMouseEnter={e=>e.currentTarget.style.borderColor=C.primary}
                            onMouseLeave={e=>e.currentTarget.style.borderColor=v.is_latest?C.primary:C.border}>
                            <div style={{width:6,height:6,borderRadius:"50%",
                              background:vm.dot,flexShrink:0}}/>
                            <span style={{fontSize:12,fontWeight:800,
                              color:v.is_latest?C.primary:C.muted,minWidth:24}}>
                              v{v.version_number||1}
                            </span>
                            {v.is_latest&&(
                              <span style={{fontSize:10,fontWeight:700,
                                padding:"1px 6px",background:C.primary,
                                color:"white",borderRadius:20}}>LATEST</span>
                            )}
                            <span style={{fontSize:12,color:C.muted,flex:1}}>
                              {new Date(v.created_at).toLocaleDateString("en-IN",
                                {day:"2-digit",month:"short",year:"numeric"})}
                              {v.version_note&&` · ${v.version_note}`}
                            </span>
                            {rm&&(
                              <span style={{fontSize:11,fontWeight:600,
                                padding:"2px 8px",borderRadius:20,
                                background:rm.bg,color:rm.text}}>
                                {rm.label}
                              </span>
                            )}
                            {v.risk_level&&<RiskBadge level={v.risk_level}/>}
                            <span style={{fontSize:12,color:C.primary,fontWeight:600}}>
                              Open →
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}

            {Math.ceil(total/PAGE_SIZE)>1 && (
              <Pagination page={page} totalPages={Math.ceil(total/PAGE_SIZE)}
                total={total} pageSize={PAGE_SIZE} onPage={setPage}/>
            )}
          </>
        )}
      </div>

      {/* Toast */}
      {toast&&(
        <div style={{position:"fixed",bottom:24,right:24,background:"#1C1B2E",
          color:"white",padding:"14px 20px",borderRadius:12,fontSize:14,
          fontWeight:500,boxShadow:"0 8px 24px rgba(0,0,0,0.3)",zIndex:9999}}>
          {toast}
        </div>
      )}
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
