"use client";
import { API_URL as API } from "@/lib/config";
export const dynamic = "force-dynamic";
import Link from "next/link";
import { ClauStorLoader } from "@/components/shared/ClauStorLoader";
import { Pagination } from "@/components/shared/Pagination";
import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { getToken } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { can } from "@/lib/permissions";
import { CounterpartyView } from "@/components/contracts/CounterpartyView";
import { C } from "@/lib/design-tokens";


const RISK_META: Record<string,{bg:string,text:string,dot:string}> = {
  high:   {bg:"#FEF2F2",text:"#DC2626",dot:"#EF4444"},
  medium: {bg:"#FFFBEB",text:"#D97706",dot:"#F59E0B"},
  low:    {bg:"#F0FDF4",text:"#16A34A",dot:"#22C55E"},
};
function formatValue(v: number | null | undefined): string {
  if (!v) return "—";
  if (v >= 10000000) return `$${(v/1000000).toFixed(1)}M`;
  if (v >= 100000)   return `$${(v/1000).toFixed(0)}K`;
  return `$${v.toLocaleString()}`;
}

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
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<"list"|"counterparty">("list");
  const [counterpartyGroups, setCounterpartyGroups] = useState<any>(null);
  const [counterpartyLoading, setCounterpartyLoading] = useState(false);
  const [uploadedBy, setUploadedBy]   = useState("");
  const [contractType, setContractType] = useState("");
  const [counterpartyFilter, setCounterpartyFilter] = useState("");
  const [dateFrom, setDateFrom]       = useState("");
  const [dateTo, setDateTo]           = useState("");
  const [valueMin, setValueMin]       = useState("");
  const [valueMax, setValueMax]       = useState("");
  const [expiryDays, setExpiryDays]   = useState("");
  const [orgUsers, setOrgUsers]       = useState<any[]>([]);
  const [loading, setLoading]     = useState(true);
  const [uploads, setUploads]     = useState<UploadState[]>([]);
  const [toast, setToast]         = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded]   = useState<Set<string>>(new Set());
  const fileRef = useRef<HTMLInputElement>(null);
  const [pageSize, setPageSize] = useState(20);

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
      page:String(page), page_size:String(pageSize),
      ...(search && {search}),
      ...(risk && {risk_level:risk}),
      ...(status && {status}),
      ...(uploadedBy && {uploaded_by:uploadedBy}),
      ...(contractType && {contract_type:contractType}),
      ...(counterpartyFilter && {counterparty:counterpartyFilter}),
      ...(dateFrom && {date_from:dateFrom}),
      ...(dateTo && {date_to:dateTo}),
      ...(valueMin && {value_min:valueMin}),
      ...(valueMax && {value_max:valueMax}),
      ...(expiryDays && {expiry_days:expiryDays}),
    });
    try {
      const r = await fetch(`${API}/api/v1/contracts/grouped?${params}`,
        {headers:{Authorization:`Bearer ${token}`}});
      const d = await r.json();
      setContracts(d.contracts||[]);
      setTotal(d.total||0);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  }, [page, pageSize, search, risk, status, uploadedBy, contractType, counterpartyFilter, dateFrom, dateTo, valueMin, valueMax, expiryDays]);

  useEffect(()=>{ load(); },[load]);

  // Fetch counterparty grouped data
  useEffect(() => {
    if (viewMode !== "counterparty") return;
    setCounterpartyLoading(true);
    const token = getToken();
    if (!token) return;
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (risk) params.set("risk_level", risk);
    if (expiryDays) params.set("expiry_days", expiryDays);
    fetch(`${API}/api/v1/contracts/by-counterparty?${params}`,
      {headers:{Authorization:`Bearer ${token}`}})
      .then(r => r.json())
      .then(d => { setCounterpartyGroups(d); setCounterpartyLoading(false); })
      .catch(() => setCounterpartyLoading(false));
  }, [viewMode, search, risk, expiryDays]);

  const activeFilterCount = [uploadedBy, contractType, counterpartyFilter,
    dateFrom, dateTo, valueMin, valueMax, expiryDays].filter(Boolean).length;


  // Load org users for "Uploaded by" filter
  useEffect(()=>{
    const token = getToken();
    if(!token) return;
    fetch(`${API}/api/v1/users/`,{headers:{Authorization:`Bearer ${token}`}})
      .then(r=>r.json()).then(d=>setOrgUsers(d.users||[])).catch(()=>{});
  },[]);

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
          else {
            let detail = "Upload failed";
            try { detail = JSON.parse(xhr.responseText).detail || detail; } catch(e){}
            reject(new Error(detail));
          }
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
    } catch(e:any){
      const msg = e.message || "Upload failed";
      const isLimit = msg.toLowerCase().includes("limit") || msg.toLowerCase().includes("upgrade");
      update({
        error: isLimit
          ? "⚠️ Contract limit reached. Upgrade your plan to upload more."
          : msg,
        status:"failed"
      });
      if (isLimit) setToast("⚠️ Contract limit reached — upgrade your plan to continue.");
    }
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
        alignItems:"center",marginBottom:20,gap:10}}>
        <div>
          <h1 style={{fontSize:22,fontWeight:800,color:C.heading,marginBottom:2}}>
            Contracts
          </h1>
          <p style={{fontSize:13,color:C.muted}}>{total} contract families</p>
        </div>

        {/* Right actions */}
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          {/* View toggle */}
          <div style={{display:"flex",borderRadius:8,border:"1px solid #E2E8F0",overflow:"hidden"}}>
            <button onClick={()=>setViewMode("list")}
              style={{padding:"6px 12px",fontSize:12,fontWeight:viewMode==="list"?700:400,
                background:viewMode==="list"?"#EFF6FF":"white",
                color:viewMode==="list"?"#2563EB":"#64748B",
                border:"none",cursor:"pointer",transition:"all 0.15s"}}>
              ☰ List
            </button>
            <button onClick={()=>setViewMode("counterparty")}
              style={{padding:"6px 12px",fontSize:12,fontWeight:viewMode==="counterparty"?700:400,
                background:viewMode==="counterparty"?"#EFF6FF":"white",
                color:viewMode==="counterparty"?"#2563EB":"#64748B",
                border:"none",cursor:"pointer",borderLeft:"1px solid #E2E8F0",transition:"all 0.15s"}}>
              🏢 By Counterparty
            </button>
          </div>
          {/* Refresh */}
          <button
            onClick={()=>{ setPage(1); viewMode==="counterparty"?setCounterpartyGroups(null):load(); setCounterpartyLoading(viewMode==="counterparty"); }}
            title="Refresh"
            style={{
              width:34, height:34, borderRadius:8,
              border:"1px solid #E2E8F0", background:"white",
              cursor:"pointer", display:"flex",
              alignItems:"center", justifyContent:"center",
              color:"#64748B", fontSize:18, fontWeight:300,
              transition:"all 0.15s",
            }}
            onMouseEnter={e=>(e.currentTarget as HTMLElement).style.background="#F8FAFC"}
            onMouseLeave={e=>(e.currentTarget as HTMLElement).style.background="white"}
          >↻</button>

          {/* Page size */}
          <select
            value={pageSize}
            onChange={e=>{ setPageSize(Number(e.target.value)); setPage(1); }}
            style={{
              padding:"6px 8px", borderRadius:8,
              border:"1px solid #E2E8F0", fontSize:12,
              color:"#374151", background:"white", cursor:"pointer",
              height:34,
            }}>
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
            <option value={100}>100 / page</option>
          </select>


        </div>
      </div>


      {/* ── Filter bar ──────────────────────────────────────────────────── */}
      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8}}>
        {/* Filters toggle */}
        <button
          onClick={()=>setShowFilters(f=>!f)}
          style={{
            display:"flex",alignItems:"center",gap:6,
            padding:"6px 12px",borderRadius:8,fontSize:12,fontWeight:600,
            border:"1px solid #E2E8F0",cursor:"pointer",
            background:showFilters?"#EFF6FF":"white",
            color:showFilters?"#0066FF":"#374151",
            transition:"all 0.15s",
          }}>
          <span>⚙</span>
          Filters
          {activeFilterCount > 0 && (
            <span style={{
              background:"#0066FF",color:"white",
              borderRadius:"50%",width:16,height:16,
              fontSize:9,fontWeight:800,
              display:"flex",alignItems:"center",justifyContent:"center",
            }}>{activeFilterCount}</span>
          )}
          <span style={{fontSize:10}}>{showFilters?"▲":"▼"}</span>
        </button>

        {/* Active filter chips */}
        {uploadedBy && (
          <span style={{fontSize:11,padding:"3px 8px",borderRadius:20,
            background:"#EFF6FF",color:"#0066FF",border:"1px solid #DBEAFE",
            display:"flex",alignItems:"center",gap:4}}>
            👤 {orgUsers.find(u=>u.id===uploadedBy)?.full_name||"User"}
            <button onClick={()=>setUploadedBy("")}
              style={{background:"none",border:"none",cursor:"pointer",
                color:"#0066FF",fontSize:12,padding:0}}>×</button>
          </span>
        )}
        {contractType && (
          <span style={{fontSize:11,padding:"3px 8px",borderRadius:20,
            background:"#EFF6FF",color:"#0066FF",border:"1px solid #DBEAFE",
            display:"flex",alignItems:"center",gap:4}}>
            📂 {contractType}
            <button onClick={()=>setContractType("")}
              style={{background:"none",border:"none",cursor:"pointer",
                color:"#0066FF",fontSize:12,padding:0}}>×</button>
          </span>
        )}
        {expiryDays && (
          <span style={{fontSize:11,padding:"3px 8px",borderRadius:20,
            background:"#FFF7ED",color:"#D97706",border:"1px solid #FDE68A",
            display:"flex",alignItems:"center",gap:4}}>
            ⏰ Expiring in {expiryDays}d
            <button onClick={()=>setExpiryDays("")}
              style={{background:"none",border:"none",cursor:"pointer",
                color:"#D97706",fontSize:12,padding:0}}>×</button>
          </span>
        )}
        {activeFilterCount > 0 && (
          <button
            onClick={()=>{
              setUploadedBy(""); setContractType(""); setCounterpartyFilter("");
              setDateFrom(""); setDateTo(""); setValueMin("");
              setValueMax(""); setExpiryDays("");
            }}
            style={{fontSize:11,color:"#EF4444",background:"none",
              border:"none",cursor:"pointer",fontWeight:600}}>
            Clear all ×
          </button>
        )}
      </div>

      {/* ── Advanced filter panel ────────────────────────────────────────── */}
      {showFilters && (
        <div style={{
          background:"white",border:"1px solid #E2E8F0",
          borderRadius:12,padding:"16px 20px",marginBottom:16,
          boxShadow:"0 4px 12px rgba(0,0,0,0.06)",
          display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,
        }}>
          {/* Uploaded by */}
          <div>
            <label style={{fontSize:11,fontWeight:600,color:"#6B7280",
              display:"block",marginBottom:4}}>👤 Uploaded By</label>
            <select value={uploadedBy} onChange={e=>setUploadedBy(e.target.value)}
              style={{width:"100%",padding:"7px 8px",borderRadius:8,
                border:"1px solid #E2E8F0",fontSize:12,color:"#374151",background:"white"}}>
              <option value="">All users</option>
              {orgUsers.map(u=>(
                <option key={u.id} value={u.id}>{u.full_name||u.email}</option>
              ))}
            </select>
          </div>

          {/* Contract type */}
          <div>
            <label style={{fontSize:11,fontWeight:600,color:"#6B7280",
              display:"block",marginBottom:4}}>📂 Contract Type</label>
            <select value={contractType} onChange={e=>setContractType(e.target.value)}
              style={{width:"100%",padding:"7px 8px",borderRadius:8,
                border:"1px solid #E2E8F0",fontSize:12,color:"#374151",background:"white"}}>
              <option value="">All types</option>
              {["MSA","NDA","License","Vendor","SaaS","Employment","Lease","Service","Other"]
                .map(t=><option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          {/* Counterparty */}
          <div>
            <label style={{fontSize:11,fontWeight:600,color:"#6B7280",
              display:"block",marginBottom:4}}>🏢 Counterparty</label>
            <input value={counterpartyFilter}
              onChange={e=>setCounterpartyFilter(e.target.value)}
              placeholder="Type company name..."
              style={{width:"100%",padding:"7px 8px",borderRadius:8,
                border:"1px solid #E2E8F0",fontSize:12,boxSizing:"border-box"}}/>
          </div>

          {/* Expiry */}
          <div>
            <label style={{fontSize:11,fontWeight:600,color:"#6B7280",
              display:"block",marginBottom:4}}>⏰ Expiring Within</label>
            <select value={expiryDays} onChange={e=>setExpiryDays(e.target.value)}
              style={{width:"100%",padding:"7px 8px",borderRadius:8,
                border:"1px solid #E2E8F0",fontSize:12,color:"#374151",background:"white"}}>
              <option value="">Any time</option>
              <option value="30">Next 30 days</option>
              <option value="60">Next 60 days</option>
              <option value="90">Next 90 days</option>
              <option value="180">Next 6 months</option>
            </select>
          </div>

          {/* Date from */}
          <div>
            <label style={{fontSize:11,fontWeight:600,color:"#6B7280",
              display:"block",marginBottom:4}}>📅 Uploaded From</label>
            <input type="date" value={dateFrom}
              onChange={e=>setDateFrom(e.target.value)}
              style={{width:"100%",padding:"7px 8px",borderRadius:8,
                border:"1px solid #E2E8F0",fontSize:12,boxSizing:"border-box"}}/>
          </div>

          {/* Date to */}
          <div>
            <label style={{fontSize:11,fontWeight:600,color:"#6B7280",
              display:"block",marginBottom:4}}>📅 Uploaded To</label>
            <input type="date" value={dateTo}
              onChange={e=>setDateTo(e.target.value)}
              style={{width:"100%",padding:"7px 8px",borderRadius:8,
                border:"1px solid #E2E8F0",fontSize:12,boxSizing:"border-box"}}/>
          </div>

          {/* Value min */}
          <div>
            <label style={{fontSize:11,fontWeight:600,color:"#6B7280",
              display:"block",marginBottom:4}}>💰 Min Value</label>
            <input type="number" value={valueMin}
              onChange={e=>setValueMin(e.target.value)}
              placeholder="e.g. 100000"
              style={{width:"100%",padding:"7px 8px",borderRadius:8,
                border:"1px solid #E2E8F0",fontSize:12,boxSizing:"border-box"}}/>
          </div>

          {/* Value max */}
          <div>
            <label style={{fontSize:11,fontWeight:600,color:"#6B7280",
              display:"block",marginBottom:4}}>💰 Max Value</label>
            <input type="number" value={valueMax}
              onChange={e=>setValueMax(e.target.value)}
              placeholder="e.g. 10000000"
              style={{width:"100%",padding:"7px 8px",borderRadius:8,
                border:"1px solid #E2E8F0",fontSize:12,boxSizing:"border-box"}}/>
          </div>
        </div>
      )}
      {/* Batch action bar */}
      {selected.size > 0 && (
        <div style={{
          display:"flex", alignItems:"center", gap:10,
          padding:"10px 16px",
          background:"#EFF6FF", border:"1px solid #DBEAFE",
          borderRadius:10, marginBottom:12,
          animation:"fadeIn 0.15s ease",
        }}>
          <span style={{fontSize:12,fontWeight:700,color:"#0066FF"}}>
            {selected.size} selected
          </span>
          <div style={{width:1,height:16,background:"#DBEAFE"}}/>
          <button
            onClick={()=>{
              const rows = displayContracts.filter(c=>selected.has(c.id));
              const csv = [
                ["Title","Counterparty","Type","Risk","Value","Expiry","Status"].join(","),
                ...rows.map(c=>[
                  `"${c.title||""}"`,
                  `"${c.counterparty||""}"`,
                  `"${c.contract_type||""}"`,
                  c.risk_level||"",
                  c.contract_value||"",
                  c.expiry_date||"",
                  c.status||""
                ].join(","))
              ].join("\n");
              const blob = new Blob([csv],{type:"text/csv"});
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href=url; a.download="contracts.csv"; a.click();
              URL.revokeObjectURL(url);
            }}
            style={{fontSize:12,fontWeight:600,color:"#374151",
              background:"white",border:"1px solid #E2E8F0",
              borderRadius:7,padding:"5px 10px",cursor:"pointer"}}>
            📥 Export
          </button>
          <button
            onClick={()=>{
              const firstId = Array.from(selected)[0];
              if(firstId) router.push(`/dashboard/contracts/${firstId}`);
            }}
            style={{fontSize:12,fontWeight:600,color:"#374151",
              background:"white",border:"1px solid #E2E8F0",
              borderRadius:7,padding:"5px 10px",cursor:"pointer"}}>
            📋 Assign Review
          </button>
          <button
            onClick={async()=>{
              const token = getToken();
              for(const id of selected){
                await fetch(`${API}/api/v1/contracts/${id}`,
                  {method:"DELETE",headers:{Authorization:`Bearer ${token}`}});
              }
              setContracts(prev=>prev.filter(c=>!selected.has(c.id)));
              setTotal(prev=>prev-selected.size);
              setSelected(new Set());
            }}
            style={{fontSize:12,fontWeight:600,color:"#EF4444",
              background:"#FEF2F2",border:"1px solid #FCA5A5",
              borderRadius:7,padding:"5px 10px",cursor:"pointer"}}>
            🗑 Delete
          </button>
          <button
            onClick={()=>setSelected(new Set())}
            style={{marginLeft:"auto",fontSize:12,color:"#94A3B8",
              background:"none",border:"none",cursor:"pointer",fontWeight:600}}>
            Clear ×
          </button>
        </div>
      )}

      {/* ── View Mode Switch ─────────────────────────────────────── */}
      {viewMode === "counterparty" ? (
        <CounterpartyView
          groups={counterpartyGroups?.groups || []}
          totalCounterparties={counterpartyGroups?.total_counterparties || 0}
          totalContracts={counterpartyGroups?.total_contracts || 0}
          portfolioValue={counterpartyGroups?.portfolio_value || 0}
          loading={counterpartyLoading}
        />
      ) : (
      <>
      {/* ── Table ───────────────────────────────────────────────────────── */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,
        borderRadius:12,overflow:"visible",
        boxShadow:"0 1px 3px rgba(0,0,0,0.06)"}}>

        {loading ? (
<div style={{padding:60}}><ClauStorLoader size={44} text="LOADING" /></div>
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
              gridTemplateColumns:"36px minmax(180px,2fr) minmax(120px,1.5fr) 120px 100px 130px 80px",
              padding:"10px 20px",background:"#F8F9FF",
              borderBottom:`2px solid ${C.border}`}}>
              <input type="checkbox"
                  style={{cursor:"pointer",accentColor:"#0066FF"}}
                  checked={selected.size===displayContracts.length && displayContracts.length>0}
                  onChange={e=>setSelected(e.target.checked ? new Set(displayContracts.map(c=>c.id)) : new Set())}
                />
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
                    gridTemplateColumns:"36px minmax(180px,2fr) minmax(120px,1.5fr) 120px 100px 130px 80px",
                    padding:"14px 20px",alignItems:"center",
                    background:isExpanded ? C.primaryLight
                      : c.risk_level==="high" ? "#FFF9F9"
                      : c.risk_level==="medium" ? "#FFFDF5"
                      : C.surface,
                    borderLeft: c.risk_level==="high" ? "3px solid #EF4444"
                      : c.risk_level==="medium" ? "3px solid #F59E0B"
                      : "3px solid transparent",
                    transition:"background 0.15s"}}
                    onMouseEnter={e=>{
                      if(!isExpanded) e.currentTarget.style.background=
                        c.risk_level==="high"?"#FEF2F2":
                        c.risk_level==="medium"?"#FFFBEB":"#F8FAFC";
                    }}
                    onMouseLeave={e=>{
                      if(!isExpanded) e.currentTarget.style.background=
                        c.risk_level==="high"?"#FFF9F9":
                        c.risk_level==="medium"?"#FFFDF5":C.surface;
                    }}>

                    {/* Checkbox */}
                    <input type="checkbox"
                      style={{cursor:"pointer",accentColor:"#0066FF"}}
                      checked={selected.has(c.id)}
                      onChange={e=>{
                        e.stopPropagation();
                        setSelected(prev=>{
                          const s=new Set(prev);
                          e.target.checked?s.add(c.id):s.delete(c.id);
                          return s;
                        });
                      }}
                      onClick={e=>e.stopPropagation()}
                    />
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
                        : <span style={{fontSize:10,padding:"2px 8px",borderRadius:20,
                            background:"#FFFBEB",color:"#D97706",border:"1px solid #FDE68A",
                            fontWeight:600, whiteSpace:"nowrap"}}>Needs Review</span>}
                    </div>

                    {/* Action icons */}
                    <div style={{display:"flex",alignItems:"center",gap:4,justifyContent:"flex-end"}}>
                      <button
                        title="View contract"
                        onClick={()=>router.push(`/dashboard/contracts/${c.id}`)}
                        style={{width:28,height:28,borderRadius:7,border:"1px solid #E2E8F0",
                          background:"white",cursor:"pointer",fontSize:13,
                          display:"flex",alignItems:"center",justifyContent:"center"}}>
                        🔍
                      </button>
                      <button
                        title="Open in Copilot"
                        onClick={()=>router.push(`/dashboard/copilot?contract=${c.id}`)}
                        style={{width:28,height:28,borderRadius:7,border:"1px solid #E2E8F0",
                          background:"white",cursor:"pointer",fontSize:13,
                          display:"flex",alignItems:"center",justifyContent:"center"}}>
                        ⚡
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

            {Math.ceil(total/pageSize)>1 && (
              <Pagination page={page} totalPages={Math.ceil(total/pageSize)}
                total={total} pageSize={pageSize} onPage={setPage}/>
            )}
          </>
        )}
      </div>

      </>
      )}
      {/* Toast */}
      {toast&&(
        <div style={{position:"fixed",bottom:24,right:24,background:"#1C1B2E",
          color:"white",padding:"14px 20px",borderRadius:12,fontSize:14,
          fontWeight:500,boxShadow:"0 8px 24px rgba(0,0,0,0.3)",zIndex:9999,
          display:"flex",alignItems:"center",gap:12}}>
          <span>{toast}</span>
          {toast.includes("limit") && (
            <Link href="/dashboard/admin/billing"
              style={{color:"#60A5FA",fontWeight:700,fontSize:13,
                textDecoration:"none",whiteSpace:"nowrap"}}>
              Upgrade →
            </Link>
          )}
        </div>
      )}
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
