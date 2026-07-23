"use client";
import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { contracts as contractsAPI, Contract } from "@/lib/api";

const C = { primary:"#5B4BFF",primaryLight:"#EEF0FF",heading:"#111827",body:"#374151",muted:"#6B7280",border:"#E5E7EB",surface:"#FFFFFF",bg:"#FAFBFC",error:"#EF4444",success:"#22C55E",warning:"#F59E0B" };

function RiskBadge({ level }: { level: string }) {
  const m: Record<string,{bg:string;text:string}> = { high:{bg:"#FEF2F2",text:"#DC2626"}, medium:{bg:"#FFFBEB",text:"#D97706"}, low:{bg:"#F0FDF4",text:"#16A34A"} };
  const c = m[level] || {bg:"#F3F4F6",text:"#6B7280"};
  return <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:20,background:c.bg,color:c.text,textTransform:"uppercase"}}>{level}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const m: Record<string,{bg:string;text:string}> = { analyzed:{bg:"#F0FDF4",text:"#16A34A"}, queued:{bg:"#F5F3FF",text:"#7C3AED"}, parsing:{bg:"#EFF6FF",text:"#2563EB"}, failed:{bg:"#FEF2F2",text:"#DC2626"} };
  const c = m[status] || {bg:"#F3F4F6",text:"#6B7280"};
  return <span style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,background:c.bg,color:c.text}}>{status}</span>;
}

export default function ContractsPage() {
  const [items, setItems] = useState<Contract[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [risk, setRisk] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const d = await contractsAPI.list({ page, search: search||undefined, risk_level: risk||undefined, status: status||undefined });
      setItems(d.contracts); setTotal(d.total);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, search, risk, status]);

  const handleUpload = async (file: File) => {
    setUploading(true); setUploadMsg("");
    try {
      const r = await contractsAPI.upload(file);
      setUploadMsg(`✅ ${file.name} uploaded! Processing started.`);
      setTimeout(load, 2000);
    } catch(e:any) { setUploadMsg(`❌ Upload failed: ${e.message}`); }
    finally { setUploading(false); }
  };

  return (
    <div style={{padding:"32px 36px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:24}}>
        <div>
          <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Contracts</h1>
          <p style={{fontSize:14,color:C.muted}}>{total} total</p>
        </div>
        <button onClick={()=>fileRef.current?.click()} disabled={uploading}
          style={{background:C.primary,color:"white",border:"none",borderRadius:8,padding:"10px 20px",fontSize:14,fontWeight:600,cursor:"pointer"}}>
          {uploading ? "Uploading..." : "⬆ Upload contract"}
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.docx,.doc" style={{display:"none"}}
          onChange={e=>e.target.files?.[0] && handleUpload(e.target.files[0])} />
      </div>
      {uploadMsg && <div style={{padding:"10px 16px",borderRadius:8,background:uploadMsg.startsWith("✅")?C.primaryLight:"#FEF2F2",color:uploadMsg.startsWith("✅")?C.primary:C.error,fontSize:14,marginBottom:16}}>{uploadMsg}</div>}
      <div style={{display:"flex",gap:12,marginBottom:20,flexWrap:"wrap"}}>
        <input value={search} onChange={e=>{setSearch(e.target.value);setPage(1);}} placeholder="Search contracts..." style={{padding:"8px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13,flex:1,minWidth:200}} />
        <select value={risk} onChange={e=>{setRisk(e.target.value);setPage(1);}} style={{padding:"8px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}>
          <option value="">All risk levels</option>
          <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
        </select>
        <select value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}} style={{padding:"8px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}>
          <option value="">All statuses</option>
          <option value="analyzed">Analyzed</option><option value="queued">Queued</option><option value="failed">Failed</option>
        </select>
      </div>
      <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden"}}>
        {loading ? <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading...</div> : items.length===0 ? (
          <div style={{padding:60,textAlign:"center"}}>
            <div style={{fontSize:40,marginBottom:16}}>📄</div>
            <p style={{fontSize:15,fontWeight:600,color:C.heading,marginBottom:8}}>No contracts found</p>
            <p style={{fontSize:14,color:C.muted}}>Upload a PDF or DOCX to get started</p>
          </div>
        ) : (
          <table style={{width:"100%",borderCollapse:"collapse"}}>
            <thead><tr style={{borderBottom:`1px solid ${C.border}`}}>
              {["Title","Counterparty","Value","Risk","Status","Expiry","Clauses"].map(h=>(
                <th key={h} style={{padding:"10px 20px",textAlign:"left",fontSize:12,fontWeight:600,color:C.muted,textTransform:"uppercase",letterSpacing:"0.05em"}}>{h}</th>
              ))}
            </tr></thead>
            <tbody>{items.map(c=>(
              <tr key={c.id} style={{borderBottom:`1px solid ${C.border}`}} onMouseEnter={e=>(e.currentTarget.style.background=C.bg)} onMouseLeave={e=>(e.currentTarget.style.background="")}>
                <td style={{padding:"14px 20px"}}>
                  <Link href={`/dashboard/contracts/${c.id}`} style={{fontSize:14,fontWeight:600,color:C.heading,textDecoration:"none"}}>{c.title}</Link>
                  {c.contract_type && <div style={{fontSize:12,color:C.muted,marginTop:2}}>{c.contract_type}</div>}
                </td>
                <td style={{padding:"14px 20px",fontSize:14,color:C.body}}>{c.counterparty||"—"}</td>
                <td style={{padding:"14px 20px",fontSize:14,color:C.body}}>{c.contract_value ? `${c.contract_currency||"USD"} ${(c.contract_value/1000000).toFixed(1)}M` : "—"}</td>
                <td style={{padding:"14px 20px"}}>{c.risk_level ? <RiskBadge level={c.risk_level}/> : "—"}</td>
                <td style={{padding:"14px 20px"}}><StatusBadge status={c.status}/></td>
                <td style={{padding:"14px 20px",fontSize:13,color:C.muted}}>{c.expiry_date ? new Date(c.expiry_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}) : "—"}</td>
                <td style={{padding:"14px 20px",fontSize:14,color:C.body,textAlign:"center"}}>{c.clause_count}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
      {total > 20 && (
        <div style={{display:"flex",justifyContent:"center",gap:8,marginTop:20}}>
          <button onClick={()=>setPage(p=>Math.max(1,p-1))} disabled={page===1} style={{padding:"8px 16px",border:`1px solid ${C.border}`,borderRadius:8,background:C.surface,cursor:"pointer",fontSize:13}}>← Prev</button>
          <span style={{padding:"8px 16px",fontSize:13,color:C.muted}}>Page {page}</span>
          <button onClick={()=>setPage(p=>p+1)} disabled={items.length<20} style={{padding:"8px 16px",border:`1px solid ${C.border}`,borderRadius:8,background:C.surface,cursor:"pointer",fontSize:13}}>Next →</button>
        </div>
      )}
    </div>
  );
}
