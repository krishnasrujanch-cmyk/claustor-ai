"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { contracts as contractsAPI, Contract, getToken } from "@/lib/api";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  error:"#EF4444", success:"#22C55E", warning:"#F59E0B",
};

function RiskBadge({ level }: { level: string }) {
  const m: Record<string,any> = {
    high:{bg:"#FEF2F2",text:"#DC2626"},
    medium:{bg:"#FFFBEB",text:"#D97706"},
    low:{bg:"#F0FDF4",text:"#16A34A"},
  };
  const c = m[level]||{bg:"#F3F4F6",text:"#6B7280"};
  return <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:20,background:c.bg,color:c.text,textTransform:"uppercase"}}>{level}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const m: Record<string,any> = {
    analyzed:{bg:"#F0FDF4",text:"#16A34A"},
    queued:{bg:"#F5F3FF",text:"#7C3AED"},
    parsing:{bg:"#EFF6FF",text:"#2563EB"},
    extracting:{bg:"#FFF7ED",text:"#C2410C"},
    scoring:{bg:"#FFF7ED",text:"#C2410C"},
    indexing:{bg:"#F0FDF4",text:"#15803D"},
    failed:{bg:"#FEF2F2",text:"#DC2626"},
  };
  const c = m[status]||{bg:"#F3F4F6",text:"#6B7280"};
  return <span style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,background:c.bg,color:c.text}}>{status}</span>;
}

interface UploadState {
  file: File;
  uploadPct: number;
  contractId: string | null;
  status: string;
  step: string;
  analysisPct: number;
  error: string | null;
  done: boolean;
}

export default function ContractsPage() {
  const [items, setItems]       = useState<Contract[]>([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [search, setSearch]     = useState("");
  const [risk, setRisk]         = useState("");
  const [status, setStatus]     = useState("");
  const [loading, setLoading]   = useState(true);
  const [uploads, setUploads]   = useState<UploadState[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await contractsAPI.list({
        page, page_size: 20,
        search: search||undefined,
        risk_level: risk||undefined,
        status: status||undefined,
      });
      setItems(d.contracts); setTotal(d.total);
    } finally { setLoading(false); }
  }, [page, search, risk, status]);

  useEffect(() => { load(); }, [load]);

  // Poll processing contracts
  useEffect(() => {
    const processing = items.filter(c => ["queued","parsing","extracting","scoring","indexing"].includes(c.status));
    if (!processing.length) return;
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [items, load]);

  const handleUpload = async (file: File) => {
    const token = getToken();
    const uploadState: UploadState = {
      file, uploadPct: 0, contractId: null,
      status: "uploading", step: "Uploading file...",
      analysisPct: 0, error: null, done: false,
    };
    setUploads(prev => [...prev, uploadState]);
    const idx = uploads.length;

    const update = (patch: Partial<UploadState>) =>
      setUploads(prev => prev.map((u, i) => i === idx ? { ...u, ...patch } : u));

    try {
      // XHR for upload progress
      const contractId = await new Promise<string>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const form = new FormData();
        form.append("file", file);

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            update({ uploadPct: Math.round(e.loaded / e.total * 100) });
          }
        };

        xhr.onload = () => {
          if (xhr.status === 202) {
            const data = JSON.parse(xhr.responseText);
            resolve(data.contract_id);
          } else {
            reject(new Error(JSON.parse(xhr.responseText).detail || "Upload failed"));
          }
        };

        xhr.onerror = () => reject(new Error("Network error"));
        xhr.open("POST", `${API}/api/v1/contracts/`);
        xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        xhr.send(form);
      });

      update({ contractId, uploadPct: 100, status: "queued", step: "Queued for analysis..." });

      // Poll analysis progress
      const STEPS = ["queued","parsing","extracting","scoring","indexing","analyzed"];
      const STEP_LABELS: Record<string,string> = {
        queued:     "Queued for analysis...",
        parsing:    "Parsing document structure...",
        extracting: "Extracting clauses with AI...",
        scoring:    "Scoring risk for each clause...",
        indexing:   "Indexing into vector store...",
        analyzed:   "Analysis complete!",
      };
      const STEP_PCT: Record<string,number> = {
        queued:0, parsing:20, extracting:45, scoring:70, indexing:90, analyzed:100
      };

      await new Promise<void>((resolve, reject) => {
        const poll = setInterval(async () => {
          try {
            const r = await fetch(`${API}/api/v1/contracts/${contractId}/status`, {
              headers: { Authorization: `Bearer ${token}` }
            });
            const d = await r.json();
            const step = d.status || "queued";
            const pct = d.progress_pct ?? STEP_PCT[step] ?? 0;

            update({
              status: step,
              step: STEP_LABELS[step] || step,
              analysisPct: pct,
            });

            if (step === "analyzed") {
              clearInterval(poll);
              update({ done: true, analysisPct: 100 });
              load();
              resolve();
            } else if (step === "failed") {
              clearInterval(poll);
              update({ error: d.error || "Analysis failed" });
              reject(new Error(d.error));
            }
          } catch(e) { clearInterval(poll); reject(e); }
        }, 2000);
      });

    } catch(e: any) {
      update({ error: e.message, status: "failed" });
    }
  };

  const deleteContract = async (id: string, title: string) => {
    if (!confirm(`Delete "${title}"? This cannot be undone.`)) return;
    const token = getToken();
    await fetch(`${API}/api/v1/contracts/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` }
    });
    load();
  };

  const reprocess = async (id: string) => {
    const token = getToken();
    const r = await fetch(`${API}/api/v1/contracts/${id}/reprocess`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` }
    });
    if (r.ok) load();
    else alert("Reprocess failed — check API logs");
  };

  return (
    <div style={{padding:"32px 36px"}}>
      {/* Header */}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:24}}>
        <div>
          <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Contracts</h1>
          <p style={{fontSize:14,color:C.muted}}>{total} total</p>
        </div>
        <button onClick={()=>fileRef.current?.click()}
          style={{background:C.primary,color:"white",border:"none",borderRadius:8,padding:"10px 20px",fontSize:14,fontWeight:600,cursor:"pointer"}}>
          ⬆ Upload contract
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.docx,.doc" style={{display:"none"}}
          onChange={e=>e.target.files?.[0] && handleUpload(e.target.files[0])}/>
      </div>

      {/* Upload progress cards */}
      {uploads.filter(u=>!u.done).map((u, i) => (
        <div key={i} style={{background:C.surface,border:`1.5px solid ${u.error?C.error:C.primary}`,borderRadius:12,padding:20,marginBottom:16}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}>
            <div>
              <div style={{fontSize:14,fontWeight:700,color:C.heading}}>{u.file.name}</div>
              <div style={{fontSize:12,color:u.error?C.error:C.primary,marginTop:2}}>{u.error||u.step}</div>
            </div>
            <div style={{fontSize:13,fontWeight:700,color:u.error?C.error:C.primary}}>
              {u.error ? "Failed" : u.status==="uploading" ? `${u.uploadPct}%` : `${u.analysisPct}%`}
            </div>
          </div>

          {/* Upload progress */}
          {u.status==="uploading" && (
            <div>
              <div style={{fontSize:11,color:C.muted,marginBottom:4}}>Uploading...</div>
              <div style={{height:6,background:C.border,borderRadius:3,overflow:"hidden"}}>
                <div style={{height:"100%",width:`${u.uploadPct}%`,background:C.primary,borderRadius:3,transition:"width 0.3s"}}/>
              </div>
            </div>
          )}

          {/* Analysis progress */}
          {u.status!=="uploading" && !u.error && (
            <div>
              {/* Step indicators */}
              <div style={{display:"flex",gap:4,marginBottom:8}}>
                {["queued","parsing","extracting","scoring","indexing","analyzed"].map(step=>{
                  const done = ["queued","parsing","extracting","scoring","indexing","analyzed"]
                    .indexOf(u.status) >= ["queued","parsing","extracting","scoring","indexing","analyzed"].indexOf(step);
                  const active = u.status === step;
                  return (
                    <div key={step} style={{flex:1,textAlign:"center"}}>
                      <div style={{height:4,borderRadius:2,background:done?C.primary:C.border,marginBottom:4,
                        animation:active?"pulse 1.5s ease-in-out infinite":undefined}}/>
                      <div style={{fontSize:9,color:done?C.primary:C.muted,fontWeight:done?600:400,textTransform:"capitalize"}}>
                        {step}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div style={{height:8,background:C.border,borderRadius:4,overflow:"hidden"}}>
                <div style={{height:"100%",width:`${u.analysisPct}%`,
                  background:`linear-gradient(90deg, ${C.primary}, #06B6D4)`,
                  borderRadius:4,transition:"width 0.5s ease"}}/>
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Filters */}
      <div style={{display:"flex",gap:12,marginBottom:20,flexWrap:"wrap"}}>
        <input value={search} onChange={e=>{setSearch(e.target.value);setPage(1);}}
          placeholder="Search contracts..." style={{padding:"8px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13,flex:1,minWidth:200}}/>
        <select value={risk} onChange={e=>{setRisk(e.target.value);setPage(1);}}
          style={{padding:"8px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}>
          <option value="">All risk levels</option>
          <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
        </select>
        <select value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}}
          style={{padding:"8px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}>
          <option value="">All statuses</option>
          <option value="analyzed">Analyzed</option>
          <option value="queued">Queued</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Contracts table */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden"}}>
        {loading ? (
          <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading...</div>
        ) : items.length===0 ? (
          <div style={{padding:60,textAlign:"center"}}>
            <div style={{fontSize:40,marginBottom:16}}>📄</div>
            <p style={{fontSize:15,fontWeight:600,color:C.heading,marginBottom:8}}>No contracts found</p>
            <p style={{fontSize:14,color:C.muted}}>Upload a PDF or DOCX to get started</p>
          </div>
        ) : (
          <table style={{width:"100%",borderCollapse:"collapse"}}>
            <thead><tr style={{borderBottom:`1px solid ${C.border}`}}>
              {["Title","Counterparty","Value","Risk","Status","Expiry","Actions"].map(h=>(
                <th key={h} style={{padding:"10px 16px",textAlign:"left",fontSize:12,fontWeight:600,color:C.muted,textTransform:"uppercase",letterSpacing:"0.04em"}}>{h}</th>
              ))}
            </tr></thead>
            <tbody>{items.map(c=>(
              <tr key={c.id} style={{borderBottom:`1px solid ${C.border}`}}
                onMouseEnter={e=>(e.currentTarget.style.background=C.bg)}
                onMouseLeave={e=>(e.currentTarget.style.background="")}>
                <td style={{padding:"12px 16px"}}>
                  <Link href={`/dashboard/contracts/${c.id}`} style={{fontSize:14,fontWeight:600,color:C.heading,textDecoration:"none"}}>
                    {c.title}
                  </Link>
                  {c.contract_type && <div style={{fontSize:11,color:C.muted,marginTop:2}}>{c.contract_type}</div>}
                </td>
                <td style={{padding:"12px 16px",fontSize:13,color:C.body}}>{c.counterparty||"—"}</td>
                <td style={{padding:"12px 16px",fontSize:13,color:C.body}}>
                  {c.contract_value ? `${c.contract_currency||"USD"} ${(c.contract_value/1000000).toFixed(1)}M` : "—"}
                </td>
                <td style={{padding:"12px 16px"}}>{c.risk_level ? <RiskBadge level={c.risk_level}/> : "—"}</td>
                <td style={{padding:"12px 16px"}}>
                  <div style={{display:"flex",alignItems:"center",gap:6}}>
                    <StatusBadge status={c.status}/>
                    {["queued","parsing","extracting","scoring","indexing"].includes(c.status) && (
                      <div style={{width:12,height:12,borderRadius:"50%",border:`2px solid ${C.primary}`,borderTopColor:"transparent",animation:"spin 0.8s linear infinite"}}/>
                    )}
                  </div>
                </td>
                <td style={{padding:"12px 16px",fontSize:12,color:C.muted}}>
                  {c.expiry_date ? new Date(c.expiry_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}) : "—"}
                </td>
                <td style={{padding:"12px 16px"}}>
                  <div style={{display:"flex",gap:6}}>
                    {c.status==="failed" && (
                      <button onClick={()=>reprocess(c.id)}
                        style={{padding:"4px 10px",border:`1px solid ${C.warning}`,borderRadius:6,background:"none",color:C.warning,fontSize:11,fontWeight:600,cursor:"pointer"}}>
                        ↺ Retry
                      </button>
                    )}
                    {c.status==="analyzed" && (
                      <button onClick={()=>reprocess(c.id)}
                        style={{padding:"4px 10px",border:`1px solid ${C.border}`,borderRadius:6,background:"none",color:C.muted,fontSize:11,cursor:"pointer"}}>
                        ↺ Reprocess
                      </button>
                    )}
                    <button onClick={()=>deleteContract(c.id, c.title)}
                      style={{padding:"4px 10px",border:`1px solid #FEE2E2`,borderRadius:6,background:"none",color:C.error,fontSize:11,cursor:"pointer"}}>
                      🗑
                    </button>
                  </div>
                </td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div style={{display:"flex",justifyContent:"center",gap:8,marginTop:20}}>
          <button onClick={()=>setPage(p=>Math.max(1,p-1))} disabled={page===1}
            style={{padding:"8px 16px",border:`1px solid ${C.border}`,borderRadius:8,background:C.surface,cursor:"pointer",fontSize:13}}>← Prev</button>
          <span style={{padding:"8px 16px",fontSize:13,color:C.muted}}>Page {page} of {Math.ceil(total/20)}</span>
          <button onClick={()=>setPage(p=>p+1)} disabled={items.length<20}
            style={{padding:"8px 16px",border:`1px solid ${C.border}`,borderRadius:8,background:C.surface,cursor:"pointer",fontSize:13}}>Next →</button>
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
      `}</style>
    </div>
  );
}
