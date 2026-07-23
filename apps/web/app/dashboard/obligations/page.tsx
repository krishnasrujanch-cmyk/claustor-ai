"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";

const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  warning:"#F59E0B", success:"#22C55E", error:"#EF4444",
};

const API = "http://localhost:8000";

function UrgencyBadge({ urgency }: { urgency: string }) {
  const m: Record<string,{bg:string;text:string;label:string}> = {
    urgent:  {bg:"#FEF2F2", text:"#DC2626", label:"Urgent"},
    warning: {bg:"#FFFBEB", text:"#D97706", label:"Soon"},
    normal:  {bg:"#F0FDF4", text:"#16A34A", label:"On track"},
  };
  const c = m[urgency] || m.normal;
  return <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:20,background:c.bg,color:c.text}}>{c.label}</span>;
}

export default function ObligationsPage() {
  const [alerts, setAlerts] = useState<any>(null);
  const [obligations, setObligations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState<string|null>(null);
  const [days, setDays] = useState(30);

  const load = async () => {
    setLoading(true);
    const token = getToken();
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const [alertsR, obR] = await Promise.all([
        fetch(`${API}/api/v1/alerts/upcoming?days=${days}`, { headers }).then(r=>r.json()),
        fetch(`${API}/api/v1/obligations/`, { headers }).then(r=>r.json()),
      ]);
      setAlerts(alertsR);
      setObligations(obR.obligations || []);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [days]);

  const markComplete = async (id: string) => {
    setCompleting(id);
    const token = getToken();
    try {
      await fetch(`${API}/api/v1/alerts/obligations/${id}/complete`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      await load();
    } finally { setCompleting(null); }
  };

  return (
    <div style={{ padding:"32px 36px" }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:24 }}>
        <div>
          <h1 style={{ fontSize:24, fontWeight:800, color:C.heading, marginBottom:4 }}>Obligations</h1>
          <p style={{ fontSize:14, color:C.muted }}>Track payment dates, renewal notices, and deadlines</p>
        </div>
        <select value={days} onChange={e=>setDays(Number(e.target.value))}
          style={{ padding:"8px 12px", border:`1.5px solid ${C.border}`, borderRadius:8, fontSize:13 }}>
          <option value={7}>Next 7 days</option>
          <option value={30}>Next 30 days</option>
          <option value={60}>Next 60 days</option>
          <option value={90}>Next 90 days</option>
        </select>
      </div>

      {/* Summary cards */}
      {alerts && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))", gap:16, marginBottom:24 }}>
          {[
            { label:"Upcoming renewals", value:alerts.summary?.total_renewals||0, color:C.primary },
            { label:"Pending obligations", value:alerts.summary?.total_obligations||0, color:C.warning },
            { label:"Urgent items", value:alerts.summary?.urgent||0, color:C.error },
            { label:"All obligations", value:obligations.length, color:C.success },
          ].map(s=>(
            <div key={s.label} style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:"16px 20px" }}>
              <div style={{ fontSize:12, color:C.muted, marginBottom:6 }}>{s.label}</div>
              <div style={{ fontSize:28, fontWeight:800, color:s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Upcoming renewals */}
      {alerts?.renewals?.length > 0 && (
        <div style={{ background:C.surface, border:`1.5px solid ${C.primary}30`, borderRadius:12, marginBottom:20, overflow:"hidden" }}>
          <div style={{ padding:"14px 20px", background:C.primaryLight, borderBottom:`1px solid ${C.border}` }}>
            <span style={{ fontSize:14, fontWeight:700, color:C.primary }}>⏰ Upcoming Renewals ({alerts.renewals.length})</span>
          </div>
          <table style={{ width:"100%", borderCollapse:"collapse" }}>
            <thead><tr style={{ borderBottom:`1px solid ${C.border}` }}>
              {["Contract","Counterparty","Expiry","Days left","Auto-renewal","Urgency"].map(h=>(
                <th key={h} style={{ padding:"10px 20px", textAlign:"left", fontSize:12, fontWeight:600, color:C.muted, textTransform:"uppercase" }}>{h}</th>
              ))}
            </tr></thead>
            <tbody>{alerts.renewals.map((r:any)=>(
              <tr key={r.id} style={{ borderBottom:`1px solid ${C.border}` }}>
                <td style={{ padding:"12px 20px", fontSize:14, fontWeight:600, color:C.heading }}>{r.title}</td>
                <td style={{ padding:"12px 20px", fontSize:13, color:C.body }}>{r.counterparty||"—"}</td>
                <td style={{ padding:"12px 20px", fontSize:13, color:C.body }}>{r.expiry_date ? new Date(r.expiry_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}) : "—"}</td>
                <td style={{ padding:"12px 20px" }}>
                  <span style={{ fontSize:13, fontWeight:700, color:r.days_until_expiry<=30?C.error:r.days_until_expiry<=60?C.warning:C.success }}>
                    {r.days_until_expiry}d
                  </span>
                </td>
                <td style={{ padding:"12px 20px", fontSize:13, color:C.body }}>{r.auto_renewal===null?"Unknown":r.auto_renewal?"Yes":"No"}</td>
                <td style={{ padding:"12px 20px" }}><UrgencyBadge urgency={r.urgency}/></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {/* All obligations */}
      <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, overflow:"hidden" }}>
        <div style={{ padding:"14px 20px", borderBottom:`1px solid ${C.border}`, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <span style={{ fontSize:14, fontWeight:700, color:C.heading }}>All Obligations</span>
          <span style={{ fontSize:13, color:C.muted }}>{obligations.length} total</span>
        </div>
        {loading ? (
          <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading...</div>
        ) : obligations.length === 0 ? (
          <div style={{ padding:60, textAlign:"center" }}>
            <div style={{ fontSize:48, marginBottom:16 }}>📅</div>
            <p style={{ fontSize:15, fontWeight:600, color:C.heading, marginBottom:8 }}>No obligations yet</p>
            <p style={{ fontSize:14, color:C.muted }}>Analyse contracts to extract obligations automatically</p>
          </div>
        ) : (
          <table style={{ width:"100%", borderCollapse:"collapse" }}>
            <thead><tr style={{ borderBottom:`1px solid ${C.border}` }}>
              {["Title","Type","Party","Due Date","Amount","Status","Action"].map(h=>(
                <th key={h} style={{ padding:"10px 20px", textAlign:"left", fontSize:12, fontWeight:600, color:C.muted, textTransform:"uppercase" }}>{h}</th>
              ))}
            </tr></thead>
            <tbody>{obligations.map((ob:any)=>(
              <tr key={ob.id} style={{ borderBottom:`1px solid ${C.border}`, opacity:ob.status==="completed"?0.6:1 }}>
                <td style={{ padding:"12px 20px", fontSize:14, fontWeight:600, color:C.heading }}>{ob.title}</td>
                <td style={{ padding:"12px 20px", fontSize:13, color:C.body }}>{ob.obligation_type}</td>
                <td style={{ padding:"12px 20px", fontSize:13, color:C.body }}>{ob.party||"—"}</td>
                <td style={{ padding:"12px 20px", fontSize:13, color:ob.due_date&&new Date(ob.due_date)<new Date()?C.error:C.body }}>
                  {ob.due_date ? new Date(ob.due_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}) : "—"}
                </td>
                <td style={{ padding:"12px 20px", fontSize:13, color:C.body }}>
                  {ob.amount ? `${ob.currency||"USD"} ${ob.amount.toLocaleString()}` : "—"}
                </td>
                <td style={{ padding:"12px 20px" }}>
                  <span style={{ fontSize:11, fontWeight:600, padding:"2px 8px", borderRadius:20,
                    background:ob.status==="completed"?"#F0FDF4":ob.status==="overdue"?"#FEF2F2":"#FFFBEB",
                    color:ob.status==="completed"?C.success:ob.status==="overdue"?C.error:C.warning }}>
                    {ob.status}
                  </span>
                </td>
                <td style={{ padding:"12px 20px" }}>
                  {ob.status === "pending" && (
                    <button onClick={()=>markComplete(ob.id)} disabled={completing===ob.id}
                      style={{ padding:"4px 12px", background:"none", border:`1px solid ${C.success}`, borderRadius:6, color:C.success, fontSize:12, fontWeight:600, cursor:"pointer" }}>
                      {completing===ob.id ? "..." : "✓ Done"}
                    </button>
                  )}
                </td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
