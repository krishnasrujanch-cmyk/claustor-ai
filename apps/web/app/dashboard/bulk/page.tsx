"use client";
export const dynamic = "force-dynamic";

import { useRef, useState, useEffect } from "react";
import { getToken } from "@/lib/api";
import { C } from "@/lib/design-tokens";
import { ClauStorLoader } from "@/components/shared/ClauStorLoader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export default function BulkImportPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [job, setJob] = useState<any>(null);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);

  // Load past bulk import jobs
  useEffect(() => {
    const token = getToken();
    if (!token) { setLoadingJobs(false); return; }
    fetch(`${API}/api/v1/bulk/jobs`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : { jobs: [] })
      .then(d => { setJobs(d.jobs || []); })
      .catch(() => {})
      .finally(() => setLoadingJobs(false));
  }, []);

  // Poll active job status
  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    const interval = setInterval(async () => {
      const token = getToken();
      const r = await fetch(`${API}/api/v1/bulk/${job.job_id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (r.ok) {
        const d = await r.json();
        setJob(d);
        if (d.status === "completed" || d.status === "failed") {
          clearInterval(interval);
          // Refresh jobs list
          fetch(`${API}/api/v1/bulk/jobs`, {
            headers: { Authorization: `Bearer ${token}` }
          }).then(r => r.json()).then(d => setJobs(d.jobs || []));
        }
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [job]);

  const handleUpload = async (file: File) => {
    if (!file.name.endsWith(".zip")) {
      setError("Please upload a ZIP file containing your PDF/DOCX contracts");
      return;
    }
    setUploading(true); setError(""); setJob(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const token = getToken();
      const r = await fetch(`${API}/api/v1/bulk/`, {
        method:"POST",
        headers:{Authorization:`Bearer ${token}`},
        body:form,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail||"Upload failed");
      setJob(data);
    } catch(e:any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  return (
    <div style={{padding:"32px 36px",maxWidth:800}}>
      <div style={{marginBottom:32}}>
        <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Bulk Import</h1>
        <p style={{fontSize:14,color:C.muted}}>Upload a ZIP file containing multiple contracts. All files are processed automatically.</p>
      </div>

      {/* Instructions */}
      <div style={{background:C.primaryLight,border:`1px solid ${C.primary}30`,borderRadius:12,padding:20,marginBottom:24}}>
        <div style={{fontSize:13,fontWeight:700,color:C.primary,marginBottom:8}}>How it works</div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
          {[
            "📁 Create a ZIP file with your PDF/DOCX contracts",
            "⬆️ Upload ZIP (max 200MB, max 50 files)",
            "🤖 Each contract is analyzed by AI automatically",
            "📊 View results in the Contracts page",
          ].map(s=><div key={s} style={{fontSize:13,color:C.body}}>{s}</div>)}
        </div>
      </div>

      {/* Upload zone */}
      {!job && (
        <div
          onDragOver={e=>{e.preventDefault();setDragging(true);}}
          onDragLeave={()=>setDragging(false)}
          onDrop={handleDrop}
          onClick={()=>fileRef.current?.click()}
          style={{
            border:`2px dashed ${dragging?C.primary:C.border}`,
            borderRadius:16, padding:"60px 40px",
            textAlign:"center", cursor:"pointer",
            background:dragging?C.primaryLight:C.surface,
            transition:"all 0.15s",
            marginBottom:20,
          }}>
          <div style={{fontSize:48,marginBottom:16}}>📦</div>
          <h3 style={{fontSize:17,fontWeight:700,color:C.heading,marginBottom:8}}>
            {uploading ? "Uploading..." : "Drop ZIP file here or click to browse"}
          </h3>
          <p style={{fontSize:13,color:C.muted,marginBottom:16}}>
            Supports ZIP files containing PDF and DOCX contracts
          </p>
          {!uploading && (
            <div style={{display:"inline-block",padding:"10px 24px",background:C.primary,color:"white",borderRadius:8,fontSize:14,fontWeight:600}}>
              Choose ZIP file
            </div>
          )}
          {uploading && (
            <div style={{display:"flex",justifyContent:"center",gap:4}}>
              {[0,1,2].map(i=><div key={i} style={{width:8,height:8,borderRadius:"50%",background:C.primary,animation:`bounce 1s ease-in-out ${i*0.15}s infinite`}}/>)}
            </div>
          )}
        </div>
      )}

      <input ref={fileRef} type="file" accept=".zip" style={{display:"none"}}
        onChange={e=>e.target.files?.[0] && handleUpload(e.target.files[0])} />

      {/* Error */}
      {error && (
        <div style={{padding:"12px 16px",background:"#FEF2F2",border:"1px solid #FEE2E2",borderRadius:8,fontSize:14,color:C.error,marginBottom:16}}>
          ❌ {error}
        </div>
      )}

      {/* Results */}
      {job && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden"}}>
          <div style={{padding:"16px 24px",background:job.status==="completed"?C.primaryLight:job.status==="partial"?"#FFFBEB":C.bg,borderBottom:`1px solid ${C.border}`}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <div>
                <div style={{fontSize:15,fontWeight:700,color:C.heading,marginBottom:4}}>
                  {job.status==="completed" ? "✅ Import Complete" : "⚠️ Partial Import"}
                </div>
                <div style={{fontSize:13,color:C.muted}}>{job.message}</div>
              </div>
              <div style={{textAlign:"right"}}>
                <div style={{fontSize:28,fontWeight:800,color:C.success}}>{job.succeeded}</div>
                <div style={{fontSize:11,color:C.muted}}>succeeded</div>
              </div>
            </div>

            {/* Progress bar */}
            <div style={{marginTop:16}}>
              <div style={{display:"flex",justifyContent:"space-between",fontSize:12,color:C.muted,marginBottom:4}}>
                <span>{job.succeeded} succeeded · {job.failed} failed</span>
                <span>{job.total_files} total</span>
              </div>
              <div style={{height:8,background:C.border,borderRadius:4,overflow:"hidden"}}>
                <div style={{height:"100%",width:`${(job.succeeded/Math.max(job.total_files,1))*100}%`,background:C.success,borderRadius:4}}/>
              </div>
            </div>
          </div>

          {/* File results */}
          <table style={{width:"100%",borderCollapse:"collapse"}}>
            <thead><tr style={{borderBottom:`1px solid ${C.border}`}}>
              {["Filename","Status","Contract ID / Error"].map(h=>(
                <th key={h} style={{padding:"10px 20px",textAlign:"left",fontSize:12,fontWeight:600,color:C.muted,textTransform:"uppercase"}}>{h}</th>
              ))}
            </tr></thead>
            <tbody>{job.results?.map((r:any,i:number)=>(
              <tr key={i} style={{borderBottom:`1px solid ${C.border}`}}>
                <td style={{padding:"12px 20px",fontSize:13,fontWeight:500,color:C.body}}>{r.filename}</td>
                <td style={{padding:"12px 20px"}}>
                  <span style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,
                    background:r.status==="queued"?C.primaryLight:"#FEF2F2",
                    color:r.status==="queued"?C.primary:C.error}}>
                    {r.status}
                  </span>
                </td>
                <td style={{padding:"12px 20px",fontSize:12,color:C.muted,fontFamily:"monospace"}}>
                  {r.contract_id || r.error || "—"}
                </td>
              </tr>
            ))}</tbody>
          </table>

          <div style={{padding:"16px 24px",display:"flex",gap:10}}>
            <button onClick={()=>{setJob(null);setError("");}}
              style={{padding:"10px 20px",border:`1px solid ${C.border}`,borderRadius:8,background:"none",fontSize:14,cursor:"pointer"}}>
              Upload another
            </button>
            <a href="/dashboard/contracts"
              style={{padding:"10px 20px",background:C.primary,color:"white",borderRadius:8,fontSize:14,fontWeight:600,textDecoration:"none",display:"inline-block"}}>
              View contracts →
            </a>
          </div>
        </div>
      )}

      <style>{`@keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}`}</style>

      {/* Past Import Jobs */}
      {(jobs.length > 0 || loadingJobs) && (
        <div style={{marginTop:32}}>
          <h2 style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:16}}>
            Import History
          </h2>
          {loadingJobs ? (
            <div style={{padding:32}}><ClauStorLoader text="LOADING" /></div>
          ) : (
            <div style={{background:"white",border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden"}}>
              {/* Header */}
              <div style={{display:"grid",gridTemplateColumns:"1fr 80px 80px 80px 100px 120px",
                padding:"10px 20px",background:C.bg,borderBottom:`1px solid ${C.border}`,
                fontSize:11,fontWeight:700,color:C.muted,textTransform:"uppercase",letterSpacing:"0.05em"}}>
                {["Date","Total","Done","Failed","Status","Duration"].map(h=>(
                  <div key={h}>{h}</div>
                ))}
              </div>
              {jobs.map((j,i)=>{
                const created = new Date(j.created_at||Date.now());
                const completed = j.completed_at ? new Date(j.completed_at) : null;
                const duration = completed
                  ? `${Math.round((completed.getTime()-created.getTime())/1000)}s`
                  : j.status === "processing" ? "Running..." : "—";
                const statusColor = j.status==="completed" ? "#22C55E"
                  : j.status==="failed" ? "#EF4444"
                  : j.status==="partial" ? "#F59E0B" : "#0066FF";
                return (
                  <div key={i} style={{display:"grid",
                    gridTemplateColumns:"1fr 80px 80px 80px 100px 120px",
                    padding:"12px 20px",borderBottom:i<jobs.length-1?`1px solid ${C.border}`:"none",
                    alignItems:"center",fontSize:13}}>
                    <div style={{fontWeight:600,color:C.heading}}>
                      {created.toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}
                      <div style={{fontSize:11,color:C.muted,fontWeight:400}}>
                        {created.toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"})}
                      </div>
                    </div>
                    <div style={{fontWeight:600}}>{j.total}</div>
                    <div style={{color:"#22C55E",fontWeight:600}}>{j.succeeded}</div>
                    <div style={{color:j.failed>0?"#EF4444":C.muted,fontWeight:j.failed>0?700:400}}>
                      {j.failed}
                    </div>
                    <div>
                      <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",
                        borderRadius:20,background:`${statusColor}15`,color:statusColor}}>
                        {j.status.charAt(0).toUpperCase()+j.status.slice(1)}
                      </span>
                    </div>
                    <div style={{fontSize:12,color:C.muted}}>{duration}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
