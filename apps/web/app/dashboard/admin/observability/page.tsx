"use client";
export const dynamic = "force-dynamic";
import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";
import { Zap, DollarSign, Clock, CheckCircle, AlertTriangle, Shield, TrendingUp } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DKU_ORG = "00000000-0000-0000-0000-000000000002";
const C = {
  primary:"#0066FF", primaryLight:"#E6F0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  success:"#22C55E", warning:"#F59E0B", error:"#EF4444",
};

function MetricCard({ Icon, label, value, sub, color=C.primary, bg=C.primaryLight }: any) {
  return (
    <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:"16px 20px"}}>
      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8}}>
        <div style={{width:30,height:30,borderRadius:8,background:bg,display:"flex",alignItems:"center",justifyContent:"center"}}>
          <Icon size={14} style={{color}}/>
        </div>
        <span style={{fontSize:11,color:C.muted,fontWeight:500}}>{label}</span>
      </div>
      <div style={{fontSize:22,fontWeight:900,color:C.heading}}>{value}</div>
      {sub && <div style={{fontSize:11,color:C.muted,marginTop:2}}>{sub}</div>}
    </div>
  );
}

function MiniBar({ pct, color }: { pct:number; color:string }) {
  return (
    <div style={{height:5,background:C.border,borderRadius:3,overflow:"hidden",marginTop:6}}>
      <div style={{height:"100%",width:`${Math.min(pct,100)}%`,background:color,borderRadius:3}}/>
    </div>
  );
}

export default function ObservabilityPage() {
  const [summary, setSummary]   = useState<any>(null);
  const [byRole, setByRole]     = useState<any[]>([]);
  const [byOrg, setByOrg]       = useState<any[]>([]);
  const [trend, setTrend]       = useState<any[]>([]);
  const [loading, setLoading]   = useState(true);
  const [days, setDays]         = useState(30);
  const [isDKU, setIsDKU]       = useState(false);

  const load = async () => {
    setLoading(true);
    const h = { Authorization: `Bearer ${getToken()}` };

    // Detect if DKU user from JWT
    try {
      const me = await fetch(`${API}/api/v1/auth/me`, {headers:h}).then(r=>r.json());
      const dku = me.org_id === DKU_ORG;
      setIsDKU(dku);

      const calls = [
        fetch(`${API}/api/v1/observability/summary?days=${days}`, {headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/observability/by-role?days=${days}`, {headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/observability/latency-trend?days=${days}`, {headers:h}).then(r=>r.json()),
      ];
      if (dku) calls.push(fetch(`${API}/api/v1/observability/by-org?days=${days}`, {headers:h}).then(r=>r.json()).catch(()=>({orgs:[]})));

      const results = await Promise.all(calls);
      setSummary(results[0]);
      setByRole(results[1]?.roles || []);
      setTrend(results[2]?.trend || []);
      if (dku && results[3]) setByOrg(results[3]?.orgs || []);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [days]);

  if (loading) return (
    <div style={{padding:60,textAlign:"center",color:C.muted}}>
      <div style={{width:28,height:28,borderRadius:"50%",border:`2px solid ${C.primary}`,borderTopColor:"transparent",animation:"spin 0.8s linear infinite",margin:"0 auto 10px"}}/>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      Loading AI insights...
    </div>
  );

  const noData = !summary || (summary.total_calls || 0) === 0;
  const hallPct   = Math.round((summary?.hallucination_rate||0)*100);
  const cachePct  = Math.round((summary?.cache_hit_rate||0)*100);
  const groundPct = Math.round((summary?.avg_groundedness||1)*100);

  return (
    <div style={{padding:"28px 32px",maxWidth:1060,margin:"0 auto"}}>

      {/* Header */}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:20}}>
        <div>
          <h1 style={{fontSize:20,fontWeight:800,color:C.heading,marginBottom:4}}>
            {isDKU ? "Platform AI Observability" : "AI Insights"}
          </h1>
          <p style={{fontSize:12,color:C.muted}}>
            {isDKU
              ? "Full platform LLM metrics — all organisations, costs, and quality"
              : "Your AI usage, quality, and performance metrics"}
          </p>
        </div>
        <select value={days} onChange={e=>setDays(Number(e.target.value))}
          style={{padding:"7px 12px",border:`1px solid ${C.border}`,borderRadius:8,fontSize:12,background:C.surface}}>
          {[7,14,30,60,90].map(d=><option key={d} value={d}>Last {d} days</option>)}
        </select>
      </div>

      {/* No data state */}
      {noData && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,
          padding:"40px 20px",textAlign:"center"}}>
          <div style={{fontSize:32,marginBottom:12}}>📊</div>
          <div style={{fontSize:15,fontWeight:700,color:C.heading,marginBottom:6}}>No data yet</div>
          <div style={{fontSize:13,color:C.muted}}>
            Start using the AI Copilot to see your usage metrics here.
          </div>
        </div>
      )}

      {!noData && (
        <>
          {/* Customer metrics — value-focused, no raw costs */}
          {!isDKU && (
            <>
              <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:16}}>
                <MetricCard Icon={Zap}          label="AI Queries Answered"
                  value={(summary.total_calls||0).toLocaleString()}
                  sub={`last ${days} days`}
                  color={C.primary} bg={C.primaryLight}/>
                <MetricCard Icon={CheckCircle}  label="Answer Confidence"
                  value={`${groundPct}%`}
                  sub="avg groundedness"
                  color={groundPct>=90?C.success:C.warning}
                  bg={groundPct>=90?"#F0FDF4":"#FFFBEB"}/>
                <MetricCard Icon={Clock}        label="Avg Response Time"
                  value={`${summary.avg_latency_ms||0}ms`}
                  sub={`P95: ${summary.p95_latency_ms||0}ms`}
                  color={C.warning} bg="#FFFBEB"/>
                <MetricCard Icon={Shield}       label="Security Events"
                  value={`${summary.injections_detected||0}`}
                  sub={`${summary.safety_blocks||0} queries blocked`}
                  color={(summary.injections_detected||0)>0?C.error:C.success}
                  bg={(summary.injections_detected||0)>0?"#FEF2F2":"#F0FDF4"}/>
              </div>

              <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12,marginBottom:20}}>
                {[
                  {label:"Citation Accuracy", pct:groundPct, color:groundPct>=90?C.success:C.warning, target:"Target: >98%"},
                  {label:"Cache Efficiency",  pct:cachePct,  color:cachePct>70?C.success:C.warning,   target:"Target: >70%"},
                  {label:"Hallucination Rate",pct:hallPct,   color:hallPct<2?C.success:C.error,        target:"Target: <2%", invert:true},
                ].map(m=>(
                  <div key={m.label} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:"14px 18px"}}>
                    <div style={{fontSize:11,color:C.muted,fontWeight:500,marginBottom:4}}>{m.label}</div>
                    <div style={{fontSize:20,fontWeight:900,color:m.color}}>
                      {m.invert ? `${m.pct}%` : `${m.pct}%`}
                    </div>
                    <MiniBar pct={m.invert ? 100-m.pct : m.pct} color={m.color}/>
                    <div style={{fontSize:10,color:C.muted,marginTop:4}}>{m.target}</div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* DKU internal — full metrics including costs */}
          {isDKU && (
            <>
              <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:16}}>
                <MetricCard Icon={Zap}         label="Total LLM Calls"
                  value={(summary.total_calls||0).toLocaleString()}
                  sub={`${summary.judge_calls||0} judge calls`}
                  color={C.primary} bg={C.primaryLight}/>
                <MetricCard Icon={DollarSign}  label="AI Spend"
                  value={`$${(summary.total_cost_usd||0).toFixed(4)}`}
                  sub={`${(summary.total_tokens||0).toLocaleString()} tokens`}
                  color="#22C55E" bg="#F0FDF4"/>
                <MetricCard Icon={Clock}       label="Avg Latency"
                  value={`${summary.avg_latency_ms||0}ms`}
                  sub={`P95: ${summary.p95_latency_ms||0}ms`}
                  color={C.warning} bg="#FFFBEB"/>
                <MetricCard Icon={CheckCircle} label="Avg Groundedness"
                  value={`${groundPct}%`}
                  sub={`${summary.hallucination_count||0} hallucinations`}
                  color={groundPct>=90?C.success:C.warning}
                  bg={groundPct>=90?"#F0FDF4":"#FFFBEB"}/>
              </div>

              <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:20}}>
                {[
                  {label:"Hallucination Rate", val:`${hallPct}%`,  color:hallPct>5?C.error:hallPct>2?C.warning:C.success, pct:hallPct},
                  {label:"Cache Hit Rate",      val:`${cachePct}%`, color:cachePct>70?C.success:C.warning, pct:cachePct},
                  {label:"Injections Detected", val:`${summary.injections_detected||0}`, color:(summary.injections_detected||0)>0?C.error:C.success, pct:0},
                  {label:"Safety Blocks",       val:`${summary.safety_blocks||0}`, color:C.muted, pct:0},
                ].map(m=>(
                  <div key={m.label} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:"14px 18px"}}>
                    <div style={{fontSize:11,color:C.muted,fontWeight:500,marginBottom:4}}>{m.label}</div>
                    <div style={{fontSize:20,fontWeight:900,color:m.color}}>{m.val}</div>
                    {m.pct > 0 && <MiniBar pct={m.pct} color={m.color}/>}
                  </div>
                ))}
              </div>
            </>
          )}

          {/* By role table + latency trend */}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:16}}>
            <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
              <div style={{padding:"12px 18px",borderBottom:`1px solid ${C.border}`,fontSize:13,fontWeight:700,color:C.heading}}>
                Usage by Agent Role
              </div>
              {byRole.length===0 ? (
                <div style={{padding:24,textAlign:"center",color:C.muted,fontSize:12}}>No data yet</div>
              ) : byRole.map((r:any)=>(
                <div key={r.role} style={{display:"flex",alignItems:"center",gap:10,
                  padding:"10px 18px",borderBottom:`1px solid ${C.border}`}}>
                  <div style={{flex:1}}>
                    <div style={{fontSize:12,fontWeight:700,color:C.heading,textTransform:"capitalize"}}>
                      {r.role.replace(/_/g," ")}
                    </div>
                    <div style={{fontSize:10,color:C.muted}}>{r.calls} calls · {(r.tokens||0).toLocaleString()} tokens</div>
                  </div>
                  <div style={{textAlign:"right"}}>
                    {isDKU && <div style={{fontSize:12,fontWeight:700,color:C.primary}}>${(r.cost_usd||0).toFixed(4)}</div>}
                    <div style={{fontSize:10,color:C.muted}}>{r.avg_latency_ms}ms avg</div>
                  </div>
                </div>
              ))}
            </div>

            <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
              <div style={{padding:"12px 18px",borderBottom:`1px solid ${C.border}`,fontSize:13,fontWeight:700,color:C.heading}}>
                Daily Latency Trend
              </div>
              <div style={{padding:"12px 18px"}}>
                {trend.length===0 ? (
                  <div style={{padding:24,textAlign:"center",color:C.muted,fontSize:12}}>No data yet</div>
                ) : trend.slice(0,7).map((t:any)=>(
                  <div key={t.day} style={{marginBottom:10}}>
                    <div style={{display:"flex",justifyContent:"space-between",fontSize:11,marginBottom:3}}>
                      <span style={{color:C.muted}}>{t.day}</span>
                      <span style={{color:C.heading,fontWeight:600}}>P50:{t.p50_ms}ms P95:{t.p95_ms}ms</span>
                    </div>
                    <MiniBar pct={(t.p95_ms/5000)*100}
                      color={t.p95_ms>3000?C.error:t.p95_ms>1500?C.warning:C.success}/>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* DKU only: by-org breakdown */}
          {isDKU && byOrg.length > 0 && (
            <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,marginBottom:16}}>
              <div style={{padding:"12px 18px",borderBottom:`1px solid ${C.border}`,fontSize:13,fontWeight:700,color:C.heading}}>
                Cost by Organisation
              </div>
              {byOrg.map((o:any)=>(
                <div key={o.name} style={{display:"flex",alignItems:"center",
                  gap:12,padding:"10px 18px",borderBottom:`1px solid ${C.border}`}}>
                  <div style={{flex:1}}>
                    <div style={{fontSize:12,fontWeight:700,color:C.heading}}>{o.name||"Unknown"}</div>
                    <div style={{fontSize:10,color:C.muted}}>{o.plan} · {o.calls} calls</div>
                  </div>
                  <div style={{textAlign:"right"}}>
                    <div style={{fontSize:13,fontWeight:700,color:C.primary}}>${(o.cost_usd||0).toFixed(4)}</div>
                    <div style={{fontSize:10,color:C.muted}}>{(o.tokens||0).toLocaleString()} tokens</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* DKU only: canary */}
          {isDKU && (
            <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,
              padding:"14px 18px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <div>
                <div style={{fontSize:13,fontWeight:700,color:C.heading,marginBottom:2}}>Model Degradation Canary</div>
                <div style={{fontSize:11,color:C.muted}}>5 test cases · runs weekly · alerts below 80% accuracy</div>
              </div>
              <button
                onClick={async()=>{
                  const r = await fetch(`${API}/api/v1/canary/run`,{method:"POST",headers:{Authorization:`Bearer ${getToken()}`}});
                  const d = await r.json();
                  const pct = d.accuracy !== undefined ? Math.round(d.accuracy*100)+"%" : "N/A";
                  alert(`Canary: ${d.status||"UNKNOWN"}\nAccuracy: ${pct} (${d.passed??'?'}/${d.total??'?'} passed)`);
                }}
                style={{padding:"7px 14px",background:C.primary,color:"white",
                  borderRadius:8,fontSize:12,fontWeight:700,border:"none",cursor:"pointer"}}>
                Run Now
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
