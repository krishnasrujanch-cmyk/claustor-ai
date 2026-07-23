"use client";
import { useEffect, useState } from "react";
import { contracts as contractsAPI } from "@/lib/api";

const C = { primary:"#5B4BFF", primaryLight:"#EEF0FF", heading:"#111827", body:"#374151", muted:"#6B7280", border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC", error:"#EF4444", warning:"#F59E0B", success:"#22C55E" };

export default function AnalyticsPage() {
  const [contracts, setContracts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    contractsAPI.list({ page_size: 100 })
      .then(d => setContracts(d.contracts))
      .finally(() => setLoading(false));
  }, []);

  const analyzed = contracts.filter(c => c.status === "analyzed");
  const highRisk  = analyzed.filter(c => c.risk_level === "high").length;
  const medRisk   = analyzed.filter(c => c.risk_level === "medium").length;
  const lowRisk   = analyzed.filter(c => c.risk_level === "low").length;
  const totalValue = analyzed.reduce((s,c) => s + (c.contract_value||0), 0);
  const avgRisk   = analyzed.length ? analyzed.reduce((s,c) => s + (c.risk_score||0), 0) / analyzed.length : 0;

  const contractTypes: Record<string,number> = {};
  analyzed.forEach(c => { if(c.contract_type) contractTypes[c.contract_type] = (contractTypes[c.contract_type]||0)+1; });

  return (
    <div style={{ padding:"32px 36px" }}>
      <h1 style={{ fontSize:24, fontWeight:800, color:C.heading, marginBottom:4 }}>Analytics</h1>
      <p style={{ fontSize:14, color:C.muted, marginBottom:32 }}>Contract portfolio overview</p>

      {loading ? <div style={{ textAlign:"center", padding:60, color:C.muted }}>Loading...</div> : (
        <>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(180px, 1fr))", gap:16, marginBottom:24 }}>
            {[
              { label:"Total contracts", value:contracts.length, color:C.primary },
              { label:"Analysed", value:analyzed.length, color:C.success },
              { label:"High risk", value:highRisk, color:C.error },
              { label:"Avg risk score", value:avgRisk.toFixed(0), color:C.warning },
              { label:"Total value", value:`$${(totalValue/1000000).toFixed(1)}M`, color:C.primary },
            ].map(s => (
              <div key={s.label} style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:"20px 24px" }}>
                <div style={{ fontSize:13, color:C.muted, marginBottom:8 }}>{s.label}</div>
                <div style={{ fontSize:28, fontWeight:800, color:s.color }}>{s.value}</div>
              </div>
            ))}
          </div>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
              <h2 style={{ fontSize:15, fontWeight:700, color:C.heading, marginBottom:16 }}>Risk distribution</h2>
              {[
                { label:"High risk", count:highRisk, color:C.error },
                { label:"Medium risk", count:medRisk, color:C.warning },
                { label:"Low risk", count:lowRisk, color:C.success },
              ].map(r => (
                <div key={r.label} style={{ marginBottom:12 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", fontSize:13, marginBottom:4 }}>
                    <span style={{ color:C.body }}>{r.label}</span>
                    <span style={{ fontWeight:600, color:r.color }}>{r.count}</span>
                  </div>
                  <div style={{ height:8, background:C.border, borderRadius:4, overflow:"hidden" }}>
                    <div style={{ height:"100%", width:`${analyzed.length ? (r.count/analyzed.length)*100 : 0}%`, background:r.color, borderRadius:4 }}/>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
              <h2 style={{ fontSize:15, fontWeight:700, color:C.heading, marginBottom:16 }}>Contract types</h2>
              {Object.entries(contractTypes).length === 0 ? (
                <p style={{ color:C.muted, fontSize:14 }}>No data yet</p>
              ) : Object.entries(contractTypes).map(([type, count]) => (
                <div key={type} style={{ display:"flex", justifyContent:"space-between", padding:"8px 0", borderBottom:`1px solid ${C.border}`, fontSize:14 }}>
                  <span style={{ color:C.body }}>{type}</span>
                  <span style={{ fontWeight:600, color:C.primary }}>{count}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
