"use client";
export const dynamic = "force-dynamic";
import { useEffect, useState, useCallback } from "react";
import { getToken } from "@/lib/api";
import { C } from "@/lib/design-tokens";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ACTION_ICONS: Record<string,string> = {
  contract_upload:   "⬆️", contract_view:    "👁️",
  contract_delete:   "🗑️", contract_export:   "⬇️",
  review_assigned:   "📋", review_submitted:  "✅",
  user_invited:      "👤", user_deleted:      "🗑️",
  login:             "🔐", data_export:       "📦",
  contract_reprocess:"🔄", api_key_created:   "🔑",
};

const STATUS_COLORS: Record<string,{bg:string,text:string}> = {
  SUCCESS: {bg:"#F0FDF4", text:"#16A34A"},
  FAILED:  {bg:"#FEF2F2", text:"#DC2626"},
  DENIED:  {bg:"#FFFBEB", text:"#D97706"},
  ALLOWED: {bg:"#E6F0FF", text:"#0066FF"},
};

export default function AuditPage() {
  const [logs, setLogs]             = useState<any[]>([]);
  const [summary, setSummary]       = useState<any[]>([]);
  const [total, setTotal]           = useState(0);
  const [page, setPage]             = useState(1);
  const [loading, setLoading]       = useState(true);
  const [action, setAction]         = useState("");
  const [resourceType, setResourceType] = useState("");
  const [exporting, setExporting]   = useState(false);
  const [exportingData, setExportingData] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const token = getToken();
    const h = {Authorization:`Bearer ${token}`};
    const params = new URLSearchParams({
      page: String(page), page_size:"50",
      ...(action && {action}),
      ...(resourceType && {resource_type: resourceType}),
    });
    try {
      const [logsR, summaryR] = await Promise.all([
        fetch(`${API}/api/v1/audit/?${params}`, {headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/audit/summary`, {headers:h}).then(r=>r.json()),
      ]);
      setLogs(logsR.logs||[]);
      setTotal(logsR.total||0);
      setSummary(summaryR.actions||[]);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  }, [page, action, resourceType]);

  useEffect(() => { load(); }, [load]);

  const downloadAuditCSV = async () => {
    setExporting(true);
    const token = getToken();
    const r = await fetch(`${API}/api/v1/audit/export`,
      {headers:{Authorization:`Bearer ${token}`}});
    if (r.ok) {
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href=url; a.download="claustor-audit.csv"; a.click();
    }
    setExporting(false);
  };

  const downloadDataExport = async () => {
    setExportingData(true);
    const token = getToken();
    const r = await fetch(`${API}/api/v1/audit/data-export`,
      {headers:{Authorization:`Bearer ${token}`}});
    if (r.ok) {
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href=url; a.download="claustor-data-export.zip"; a.click();
    }
    setExportingData(false);
  };

  return (
    <div style={{padding:"32px 36px",maxWidth:1200,margin:"0 auto"}}>
      {/* Header */}
      <div style={{display:"flex",justifyContent:"space-between",
        alignItems:"flex-start",marginBottom:28}}>
        <div>
          <h1 style={{fontSize:22,fontWeight:800,color:C.heading,marginBottom:4}}>
            Audit Log
          </h1>
          <p style={{fontSize:13,color:C.muted}}>
            Complete record of all actions taken on your organisation's data
          </p>
        </div>
        <div style={{display:"flex",gap:10}}>
          <button onClick={downloadAuditCSV} disabled={exporting}
            style={{padding:"9px 16px",border:`1px solid ${C.border}`,
              borderRadius:8,background:C.surface,fontSize:13,
              fontWeight:600,cursor:"pointer",color:C.body,
              display:"flex",alignItems:"center",gap:6}}>
            {exporting?"Exporting...":"📊 Export CSV"}
          </button>
          <button onClick={downloadDataExport} disabled={exportingData}
            style={{padding:"9px 16px",background:C.primary,color:"white",
              border:"none",borderRadius:8,fontSize:13,fontWeight:600,
              cursor:"pointer",display:"flex",alignItems:"center",gap:6,
              boxShadow:"0 2px 8px rgba(91,75,255,0.3)"}}>
            {exportingData?"Preparing...":"📦 Export All Data"}
          </button>
        </div>
      </div>

      {/* Activity Summary */}
      {summary.length > 0 && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:12,padding:20,marginBottom:20}}>
          <h3 style={{fontSize:14,fontWeight:700,color:C.heading,marginBottom:12}}>
            Activity (Last 30 Days)
          </h3>
          <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
            {summary.slice(0,8).map(s=>(
              <div key={s.action} style={{padding:"8px 14px",
                background:C.bg,border:`1px solid ${C.border}`,borderRadius:8,
                display:"flex",flexDirection:"column",alignItems:"center",gap:2}}>
                <span style={{fontSize:18}}>{ACTION_ICONS[s.action]||"⚡"}</span>
                <span style={{fontSize:18,fontWeight:800,color:C.heading}}>{s.count}</span>
                <span style={{fontSize:10,color:C.muted,textTransform:"uppercase",
                  letterSpacing:"0.04em"}}>
                  {s.action.replace(/_/g," ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Export Info Banner */}
      <div style={{background:"linear-gradient(135deg,#E6F0FF,#F5F3FF)",
        border:`1px solid ${C.primary}30`,borderRadius:12,
        padding:"14px 20px",marginBottom:20,
        display:"flex",alignItems:"center",gap:16}}>
        <span style={{fontSize:32}}>📦</span>
        <div style={{flex:1}}>
          <div style={{fontSize:14,fontWeight:700,color:C.heading,marginBottom:2}}>
            Data Portability
          </div>
          <div style={{fontSize:13,color:C.muted}}>
            Export all your organisation's contracts, clauses, obligations and audit history as a ZIP archive.
            Your data, always yours.
          </div>
        </div>
        <button onClick={downloadDataExport} disabled={exportingData}
          style={{padding:"9px 20px",background:C.primary,color:"white",
            border:"none",borderRadius:8,fontSize:13,fontWeight:600,
            cursor:"pointer",flexShrink:0,whiteSpace:"nowrap"}}>
          {exportingData?"📦 Preparing ZIP...":"📦 Download All Data"}
        </button>
      </div>

      {/* Filters */}
      <div style={{display:"flex",gap:10,marginBottom:16,flexWrap:"wrap"}}>
        <select value={action} onChange={e=>{setAction(e.target.value);setPage(1);}}
          style={{padding:"8px 12px",border:`1px solid ${C.border}`,
            borderRadius:8,fontSize:13,background:C.surface}}>
          <option value="">All Actions</option>
          {Object.keys(ACTION_ICONS).map(a=>(
            <option key={a} value={a}>{ACTION_ICONS[a]} {a.replace(/_/g," ")}</option>
          ))}
        </select>
        <select value={resourceType}
          onChange={e=>{setResourceType(e.target.value);setPage(1);}}
          style={{padding:"8px 12px",border:`1px solid ${C.border}`,
            borderRadius:8,fontSize:13,background:C.surface}}>
          <option value="">All Resources</option>
          <option value="contract">Contracts</option>
          <option value="review">Reviews</option>
          <option value="user">Users</option>
          <option value="organisation">Organisation</option>
        </select>
        {(action||resourceType) && (
          <button onClick={()=>{setAction("");setResourceType("");setPage(1);}}
            style={{padding:"8px 12px",background:"#FEF2F2",border:"none",
              borderRadius:8,fontSize:12,color:C.error,cursor:"pointer",fontWeight:600}}>
            ✕ Clear
          </button>
        )}
        <span style={{marginLeft:"auto",fontSize:13,color:C.muted,
          display:"flex",alignItems:"center"}}>
          {total.toLocaleString()} events
        </span>
      </div>

      {/* Audit Log Table */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,
        borderRadius:12,overflow:"hidden"}}>
        {/* Header */}
        <div style={{display:"grid",
          gridTemplateColumns:"160px 1fr 120px 100px 140px 120px",
          padding:"10px 20px",background:C.bg,
          borderBottom:`1px solid ${C.border}`}}>
          {["Timestamp","Action","Status","Role","Resource","User"].map(h=>(
            <div key={h} style={{fontSize:11,fontWeight:700,color:C.muted,
              textTransform:"uppercase",letterSpacing:"0.05em"}}>{h}</div>
          ))}
        </div>

        {loading ? (
          <div style={{padding:60,textAlign:"center",color:C.muted}}>
            Loading audit log...
          </div>
        ) : logs.length===0 ? (
          <div style={{padding:60,textAlign:"center"}}>
            <div style={{fontSize:40,marginBottom:8}}>📋</div>
            <div style={{fontSize:15,fontWeight:600,color:C.heading,marginBottom:4}}>
              No audit events yet
            </div>
            <div style={{fontSize:13,color:C.muted}}>
              Events will appear here as users interact with your contracts
            </div>
          </div>
        ) : logs.map(log=>{
          const sc = STATUS_COLORS[log.status]||{bg:C.bg,text:C.muted};
          const ts = new Date(log.created_at);
          return (
            <div key={log.id}
              style={{display:"grid",
                gridTemplateColumns:"160px 1fr 120px 100px 140px 120px",
                padding:"12px 20px",borderBottom:`1px solid ${C.border}`,
                alignItems:"center"}}>
              {/* Timestamp */}
              <div style={{fontSize:12,color:C.muted}}>
                <div>{ts.toLocaleDateString("en-IN",{day:"2-digit",month:"short"})}</div>
                <div>{ts.toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"})}</div>
              </div>
              {/* Action */}
              <div style={{display:"flex",alignItems:"center",gap:8}}>
                <span style={{fontSize:16}}>{ACTION_ICONS[log.action]||"⚡"}</span>
                <div>
                  <div style={{fontSize:13,fontWeight:600,color:C.heading}}>
                    {log.action.replace(/_/g," ")}
                  </div>
                  {log.extra_data?.title && (
                    <div style={{fontSize:11,color:C.muted}}>
                      {log.extra_data.title}
                    </div>
                  )}
                </div>
              </div>
              {/* Status */}
              <div>
                <span style={{fontSize:11,fontWeight:700,padding:"3px 8px",
                  borderRadius:20,background:sc.bg,color:sc.text}}>
                  {log.status}
                </span>
              </div>
              {/* Role */}
              <div style={{fontSize:12,color:C.muted}}>
                {log.user_role||"—"}
              </div>
              {/* Resource */}
              <div style={{fontSize:12,color:C.muted}}>
                {log.resource_type && (
                  <span>{log.resource_type}
                    {log.resource_id && (
                      <span style={{color:C.primary}}>
                        {" "}#{log.resource_id.slice(0,8)}
                      </span>
                    )}
                  </span>
                )}
              </div>
              {/* User */}
              <div style={{fontSize:12,color:C.body,
                overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                {log.user||"System"}
              </div>
            </div>
          );
        })}

        {/* Pagination */}
        {total > 50 && (
          <div style={{padding:"12px 20px",borderTop:`1px solid ${C.border}`,
            display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span style={{fontSize:13,color:C.muted}}>
              Page {page} of {Math.ceil(total/50)}
            </span>
            <div style={{display:"flex",gap:8}}>
              <button onClick={()=>setPage(p=>Math.max(1,p-1))}
                disabled={page===1}
                style={{padding:"6px 14px",border:`1px solid ${C.border}`,
                  borderRadius:8,background:C.surface,cursor:"pointer",
                  fontSize:13,color:page===1?C.muted:C.body}}>
                ← Prev
              </button>
              <button onClick={()=>setPage(p=>p+1)}
                disabled={page>=Math.ceil(total/50)}
                style={{padding:"6px 14px",border:`1px solid ${C.border}`,
                  borderRadius:8,background:C.surface,cursor:"pointer",
                  fontSize:13}}>
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
