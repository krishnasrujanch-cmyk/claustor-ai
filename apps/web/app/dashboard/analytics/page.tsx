"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF", accent:"#06B6D4",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  error:"#EF4444", warning:"#F59E0B", success:"#22C55E",
};

const RISK_COLORS = {
  high:   { bg:"#FEF2F2", text:"#DC2626", bar:"#EF4444" },
  medium: { bg:"#FFFBEB", text:"#D97706", bar:"#F59E0B" },
  low:    { bg:"#F0FDF4", text:"#16A34A", bar:"#22C55E" },
};

// ── Mini bar chart ────────────────────────────────────
function BarChart({ data, maxValue }: { data: {label:string;value:number;color:string}[]; maxValue: number }) {
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
      {data.map(item => (
        <div key={item.label}>
          <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:4 }}>
            <span style={{ color:C.body, fontWeight:500 }}>{item.label}</span>
            <span style={{ color:C.muted }}>{item.value}</span>
          </div>
          <div style={{ height:8, background:C.border, borderRadius:4, overflow:"hidden" }}>
            <div style={{
              height:"100%",
              width:`${maxValue > 0 ? (item.value/maxValue)*100 : 0}%`,
              background:item.color,
              borderRadius:4,
              transition:"width 0.6s ease",
            }}/>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Risk Heatmap ──────────────────────────────────────
function RiskHeatmap({ matrix, clauseTypes }: { matrix:any; clauseTypes:string[] }) {
  const getColor = (score: number) => {
    if (score === 0) return { bg:"#F9FAFB", text:"#9CA3AF" };
    if (score >= 67) return { bg:"#FEE2E2", text:"#DC2626" };
    if (score >= 34) return { bg:"#FEF3C7", text:"#D97706" };
    return { bg:"#DCFCE7", text:"#16A34A" };
  };

  return (
    <div style={{ overflowX:"auto" }}>
      <table style={{ borderCollapse:"collapse", width:"100%", fontSize:12 }}>
        <thead>
          <tr>
            <th style={{ padding:"8px 12px", textAlign:"left", color:C.muted, fontWeight:600, minWidth:160 }}>Clause Type</th>
            {["Low Risk","Medium Risk","High Risk"].map(h=>(
              <th key={h} style={{ padding:"8px 16px", textAlign:"center", color:C.muted, fontWeight:600, minWidth:100 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {clauseTypes.map(ct => (
            <tr key={ct} style={{ borderTop:`1px solid ${C.border}` }}>
              <td style={{ padding:"10px 12px", color:C.body, fontWeight:500, textTransform:"capitalize" }}>
                {ct.replace(/_/g," ")}
              </td>
              {["low","medium","high"].map(rl => {
                const cell = matrix[ct]?.[rl] || { count:0, avg_score:0 };
                const c = getColor(cell.avg_score);
                return (
                  <td key={rl} style={{ padding:"8px 16px", textAlign:"center" }}>
                    {cell.count > 0 ? (
                      <div style={{
                        display:"inline-flex", flexDirection:"column", alignItems:"center",
                        background:c.bg, color:c.text,
                        borderRadius:8, padding:"6px 12px", minWidth:64,
                      }}>
                        <span style={{ fontWeight:700, fontSize:14 }}>{cell.count}</span>
                        <span style={{ fontSize:10 }}>{cell.avg_score.toFixed(0)} pts</span>
                      </div>
                    ) : (
                      <span style={{ color:"#E5E7EB", fontSize:18 }}>—</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────
function StatCard({ label, value, sub, color=C.primary }: { label:string;value:any;sub?:string;color?:string }) {
  return (
    <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:"20px 24px" }}>
      <div style={{ fontSize:12, color:C.muted, marginBottom:8, textTransform:"uppercase", letterSpacing:"0.05em" }}>{label}</div>
      <div style={{ fontSize:28, fontWeight:800, color, letterSpacing:"-0.02em" }}>{value}</div>
      {sub && <div style={{ fontSize:12, color:C.muted, marginTop:4 }}>{sub}</div>}
    </div>
  );
}

// ── Expiry Timeline ───────────────────────────────────
function ExpiryTimeline({ timeline }: { timeline:any[] }) {
  if (!timeline?.length) return (
    <div style={{ textAlign:"center", padding:40, color:C.muted }}>No contracts expiring in the next 3 years</div>
  );

  const maxCount = Math.max(...timeline.map(q=>q.count));

  return (
    <div style={{ display:"flex", gap:12, alignItems:"flex-end", overflowX:"auto", padding:"8px 0" }}>
      {timeline.map(q => (
        <div key={q.quarter} style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:6, minWidth:80 }}>
          <div style={{ fontSize:12, fontWeight:700, color:C.body }}>{q.count}</div>
          <div style={{
            width:60,
            height: Math.max((q.count/Math.max(maxCount,1))*120, 8),
            background: q.count >= 3 ? C.error : q.count >= 2 ? C.warning : C.primary,
            borderRadius:"4px 4px 0 0",
            transition:"height 0.4s ease",
            cursor:"pointer",
            title:q.contracts.map((c:any)=>c.title).join(", "),
          }}/>
          <div style={{ fontSize:10, color:C.muted, textAlign:"center" }}>{q.quarter}</div>
        </div>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────
export default function AnalyticsPage() {
  const [overview, setOverview]     = useState<any>(null);
  const [heatmap, setHeatmap]       = useState<any>(null);
  const [distribution, setDist]     = useState<any>(null);
  const [timeline, setTimeline]     = useState<any>(null);
  const [counterparty, setCp]       = useState<any>(null);
  const [loading, setLoading]       = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const h = { Authorization:`Bearer ${token}` };

    Promise.all([
      fetch(`${API}/api/v1/analytics/overview`,            {headers:h}).then(r=>r.json()),
      fetch(`${API}/api/v1/analytics/risk-heatmap`,        {headers:h}).then(r=>r.json()),
      fetch(`${API}/api/v1/analytics/clause-distribution`, {headers:h}).then(r=>r.json()),
      fetch(`${API}/api/v1/analytics/expiry-timeline`,     {headers:h}).then(r=>r.json()),
      fetch(`${API}/api/v1/analytics/counterparty-risk`,   {headers:h}).then(r=>r.json()),
    ]).then(([ov, hm, dist, tl, cp]) => {
      setOverview(ov);
      setHeatmap(hm);
      setDist(dist);
      setTimeline(tl);
      setCp(cp);
    }).catch(console.error)
    .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ padding:60, textAlign:"center", color:C.muted }}>Loading analytics...</div>
  );

  return (
    <div style={{ padding:"32px 36px" }}>
      <div style={{ marginBottom:32 }}>
        <h1 style={{ fontSize:24, fontWeight:800, color:C.heading, marginBottom:4 }}>Analytics</h1>
        <p style={{ fontSize:14, color:C.muted }}>Contract portfolio intelligence</p>
      </div>

      {/* Overview stats */}
      {overview && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))", gap:16, marginBottom:28 }}>
          <StatCard label="Total contracts"   value={overview.contracts.total}          color={C.primary} />
          <StatCard label="Analysed"          value={overview.contracts.analyzed}       color={C.success} sub="successfully processed" />
          <StatCard label="High risk"         value={overview.risk.high}                color={C.error}   sub={`avg score ${overview.risk.avg_score}`} />
          <StatCard label="Total value"       value={`$${overview.value.total_m}M`}     color={C.primary} sub="across all contracts" />
          <StatCard label="Total clauses"     value={overview.clauses.total}            color="#6366F1"   sub={`avg risk ${overview.clauses.avg_risk}`} />
          <StatCard label="Auto-renewal"      value={overview.contracts.auto_renewal}   color={C.warning} sub="contracts" />
          <StatCard label="Expiring in 90d"   value={overview.contracts.expiring_soon}  color={overview.contracts.expiring_soon>0?C.error:C.success} />
        </div>
      )}

      {/* Risk breakdown + Clause distribution */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20, marginBottom:20 }}>
        {/* Risk breakdown */}
        {overview && (
          <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
            <h2 style={{ fontSize:15, fontWeight:700, color:C.heading, marginBottom:20 }}>Risk distribution</h2>
            <BarChart
              maxValue={overview.contracts.analyzed || 1}
              data={[
                { label:`High risk (${overview.risk.high})`,   value:overview.risk.high,   color:C.error },
                { label:`Medium risk (${overview.risk.medium})`, value:overview.risk.medium, color:C.warning },
                { label:`Low risk (${overview.risk.low})`,    value:overview.risk.low,    color:C.success },
              ]}
            />
            <div style={{ marginTop:20, padding:"12px 16px", background:C.bg, borderRadius:8 }}>
              <div style={{ fontSize:12, color:C.muted, marginBottom:4 }}>Portfolio risk score</div>
              <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                <div style={{ flex:1, height:10, background:C.border, borderRadius:5, overflow:"hidden" }}>
                  <div style={{ height:"100%", width:`${overview.risk.avg_score}%`,
                    background: overview.risk.avg_score >= 67 ? C.error : overview.risk.avg_score >= 34 ? C.warning : C.success,
                    borderRadius:5 }}/>
                </div>
                <span style={{ fontSize:16, fontWeight:800,
                  color: overview.risk.avg_score >= 67 ? C.error : overview.risk.avg_score >= 34 ? C.warning : C.success }}>
                  {overview.risk.avg_score}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Clause distribution */}
        {distribution && (
          <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
            <h2 style={{ fontSize:15, fontWeight:700, color:C.heading, marginBottom:20 }}>
              Clause distribution <span style={{ fontSize:12, color:C.muted, fontWeight:400 }}>({distribution.total_clauses} total)</span>
            </h2>
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {distribution.distribution?.slice(0,8).map((item:any) => (
                <div key={item.clause_type}>
                  <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:3 }}>
                    <span style={{ color:C.body, textTransform:"capitalize" }}>{item.clause_type.replace(/_/g," ")}</span>
                    <span style={{ color:C.muted }}>{item.count} ({item.pct}%)</span>
                  </div>
                  <div style={{ height:6, background:C.border, borderRadius:3, overflow:"hidden" }}>
                    <div style={{ height:"100%", width:`${item.pct}%`,
                      background: item.avg_risk >= 67 ? C.error : item.avg_risk >= 34 ? C.warning : C.primary,
                      borderRadius:3 }}/>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Risk Heatmap */}
      {heatmap && heatmap.clause_types?.length > 0 && (
        <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24, marginBottom:20 }}>
          <div style={{ marginBottom:20 }}>
            <h2 style={{ fontSize:15, fontWeight:700, color:C.heading, marginBottom:4 }}>Risk Heatmap</h2>
            <p style={{ fontSize:13, color:C.muted }}>Clause types vs risk levels — number of clauses and average risk score</p>
          </div>
          <RiskHeatmap matrix={heatmap.matrix} clauseTypes={heatmap.clause_types} />

          {/* Ranked list */}
          {heatmap.ranked?.length > 0 && (
            <div style={{ marginTop:20, padding:"16px 0 0", borderTop:`1px solid ${C.border}` }}>
              <div style={{ fontSize:13, fontWeight:600, color:C.heading, marginBottom:12 }}>Riskiest clause types</div>
              <div style={{ display:"flex", gap:10, flexWrap:"wrap" }}>
                {heatmap.ranked.slice(0,6).map((item:any, i:number) => (
                  <div key={item.clause_type} style={{
                    display:"flex", alignItems:"center", gap:8,
                    padding:"6px 12px", borderRadius:20,
                    background: item.avg_risk >= 67 ? "#FEF2F2" : item.avg_risk >= 34 ? "#FFFBEB" : C.primaryLight,
                    border:`1px solid ${item.avg_risk >= 67 ? "#FEE2E2" : item.avg_risk >= 34 ? "#FDE68A" : C.border}`,
                  }}>
                    <span style={{ fontSize:11, fontWeight:700,
                      color: item.avg_risk >= 67 ? C.error : item.avg_risk >= 34 ? C.warning : C.primary }}>
                      #{i+1}
                    </span>
                    <span style={{ fontSize:12, color:C.body, textTransform:"capitalize" }}>
                      {item.clause_type.replace(/_/g," ")}
                    </span>
                    <span style={{ fontSize:11, color:C.muted }}>{item.avg_risk} pts</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Expiry timeline + Counterparty risk */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>
        {/* Expiry timeline */}
        {timeline && (
          <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
            <h2 style={{ fontSize:15, fontWeight:700, color:C.heading, marginBottom:4 }}>Expiry timeline</h2>
            <p style={{ fontSize:13, color:C.muted, marginBottom:20 }}>Contracts expiring by quarter (next 3 years)</p>
            <ExpiryTimeline timeline={timeline.timeline} />
          </div>
        )}

        {/* Counterparty risk */}
        {counterparty && counterparty.counterparties?.length > 0 && (
          <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
            <h2 style={{ fontSize:15, fontWeight:700, color:C.heading, marginBottom:20 }}>Counterparty risk</h2>
            <table style={{ width:"100%", borderCollapse:"collapse" }}>
              <thead><tr>
                {["Counterparty","Contracts","Avg Risk","Value"].map(h=>(
                  <th key={h} style={{ padding:"6px 0", textAlign:"left", fontSize:11, fontWeight:600, color:C.muted, textTransform:"uppercase", borderBottom:`1px solid ${C.border}` }}>{h}</th>
                ))}
              </tr></thead>
              <tbody>{counterparty.counterparties.map((cp:any) => (
                <tr key={cp.name} style={{ borderBottom:`1px solid ${C.border}` }}>
                  <td style={{ padding:"10px 0", fontSize:13, fontWeight:600, color:C.heading }}>{cp.name}</td>
                  <td style={{ padding:"10px 0", fontSize:13, color:C.body, textAlign:"center" }}>{cp.contracts}</td>
                  <td style={{ padding:"10px 0", textAlign:"center" }}>
                    <span style={{ fontSize:12, fontWeight:700, padding:"2px 8px", borderRadius:12,
                      background: cp.risk_level==="high"?"#FEF2F2":cp.risk_level==="medium"?"#FFFBEB":"#F0FDF4",
                      color: cp.risk_level==="high"?C.error:cp.risk_level==="medium"?C.warning:C.success }}>
                      {cp.avg_risk}
                    </span>
                  </td>
                  <td style={{ padding:"10px 0", fontSize:12, color:C.muted }}>
                    {cp.total_value > 0 ? `$${(cp.total_value/1000000).toFixed(1)}M` : "—"}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
