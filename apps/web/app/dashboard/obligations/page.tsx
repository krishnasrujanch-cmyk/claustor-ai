"use client";
import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";

const C = { primary:"#5B4BFF", heading:"#111827", body:"#374151", muted:"#6B7280", border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC", warning:"#F59E0B", success:"#22C55E", error:"#EF4444" };

export default function ObligationsPage() {
  const [obligations, setObligations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const token = getToken();
        const r = await fetch("http://localhost:8000/api/v1/obligations/", {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (r.ok) {
          const d = await r.json();
          setObligations(d.obligations || []);
        }
      } catch(e) { console.error(e); }
      finally { setLoading(false); }
    };
    load();
  }, []);

  const statusColor: Record<string,string> = { pending:C.warning, completed:C.success, overdue:C.error };

  return (
    <div style={{ padding:"32px 36px" }}>
      <h1 style={{ fontSize:24, fontWeight:800, color:C.heading, marginBottom:4 }}>Obligations</h1>
      <p style={{ fontSize:14, color:C.muted, marginBottom:32 }}>Track payment dates, renewal notices, and deadlines</p>

      {loading ? (
        <div style={{ textAlign:"center", padding:60, color:C.muted }}>Loading...</div>
      ) : obligations.length === 0 ? (
        <div style={{ textAlign:"center", padding:80, background:C.surface, border:`1px solid ${C.border}`, borderRadius:12 }}>
          <div style={{ fontSize:48, marginBottom:16 }}>📅</div>
          <p style={{ fontSize:16, fontWeight:700, color:C.heading, marginBottom:8 }}>No obligations yet</p>
          <p style={{ fontSize:14, color:C.muted }}>Upload and analyse contracts to track obligations</p>
        </div>
      ) : (
        <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, overflow:"hidden" }}>
          <table style={{ width:"100%", borderCollapse:"collapse" }}>
            <thead><tr style={{ borderBottom:`1px solid ${C.border}` }}>
              {["Title","Type","Party","Due Date","Amount","Status"].map(h=>(
                <th key={h} style={{ padding:"10px 20px", textAlign:"left", fontSize:12, fontWeight:600, color:C.muted, textTransform:"uppercase" }}>{h}</th>
              ))}
            </tr></thead>
            <tbody>{obligations.map((ob:any) => (
              <tr key={ob.id} style={{ borderBottom:`1px solid ${C.border}` }}>
                <td style={{ padding:"14px 20px", fontSize:14, fontWeight:600, color:C.heading }}>{ob.title}</td>
                <td style={{ padding:"14px 20px", fontSize:13, color:C.body }}>{ob.obligation_type}</td>
                <td style={{ padding:"14px 20px", fontSize:13, color:C.body }}>{ob.party || "—"}</td>
                <td style={{ padding:"14px 20px", fontSize:13, color:C.body }}>{ob.due_date ? new Date(ob.due_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}) : "—"}</td>
                <td style={{ padding:"14px 20px", fontSize:13, color:C.body }}>{ob.amount ? `${ob.currency||"INR"} ${ob.amount.toLocaleString()}` : "—"}</td>
                <td style={{ padding:"14px 20px" }}>
                  <span style={{ fontSize:11, fontWeight:600, padding:"2px 8px", borderRadius:20, background:`${statusColor[ob.status]||C.muted}20`, color:statusColor[ob.status]||C.muted }}>
                    {ob.status}
                  </span>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
