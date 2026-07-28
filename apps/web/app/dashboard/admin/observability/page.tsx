"use client";
import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";
import { Zap, DollarSign, Clock, CheckCircle } from "lucide-react";

const API = "http://localhost:8000";
const C = {
  primary:"#0066FF", primaryLight:"#E6F0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  success:"#22C55E", warning:"#F59E0B", error:"#EF4444",
};

function MetricCard({ Icon, label, value, sub, color="#0066FF", bg="#E6F0FF" }: any) {
  return (
    <div style={{background:C.surface,border:`1px solid ${C.border}`,
      borderRadius:12,padding:"16px 20px"}}>
      <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
        <div style={{width:32,height:32,borderRadius:8,background:bg,
          display:"flex",alignItems:"center",justifyContent:"center"}}>
          <Icon size={15} style={{color}}/>
        </div>
        <span style={{fontSize:12,color:C.muted,fontWeight:500}}>{label}</span>
      </div>
      <div style={{fontSize:24,fontWeight:900,color:C.heading}}>{value}</div>
      {sub && <div style={{fontSize:11,color:C.muted,marginTop:3}}>{sub}</div>}
    </div>
  );
}

function MiniBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div style={{height:6,background:C.border,borderRadius:3,overflow:"hidden"}}>
      <div style={{height:"100%",width:`${Math.min(pct,100)}%`,
        background:color,borderRadius:3}}/>
    </div>
  );
}

export default function ObservabilityPage() {
  const [summary, setSummary] = useState<any>(null);
  const [byRole, setByRole]   = useState<any[]>([]);
  const [trend, setTrend]     = useState<any[]>([]);
  const [feedback, setFeedback] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays]       = useState(30);

  const load = async () => {
    setLoading(true);
    const h = { Authorization: `Bearer ${getToken()}` };
    try {
      const [s, r, t, f] = await Promise.all([
        fetch(`${API}/api/v1/observability/summary?days=${days}`,{headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/observability/by-role?days=${days}`,{headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/observability/latency-trend?days=${days}`,{headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/observability/feedback?days=${days}`,{headers:h}).then(r=>r.json()),
      ]);
      setSummary(s); setByRole(r.roles||[]); setTrend(t.trend||[]); setFeedback(f);
    } catch(e){ console.error(e); }
    finally{ setLoading(false); }
  };

  useEffect(()=>{ load(); },[days]);

  if (loading) return (
    <div style={{padding:60,textAlign:"center",color:C.muted}}>
      <div style={{width:32,height:32,borderRadius:"50%",
        border:`2px solid ${C.primary}`,borderTopColor:"transparent",
        animation:"spin 0.8s linear infinite",margin:"0 auto 12px"}}/>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  const hallRate  = summary ? Math.round((summary.hallucination_rate||0)*100) : 0;
  const cacheRate = summary ? Math.round((summary.cache_hit_rate||0)*100) : 0;
  const groundPct = summary ? Math.round((summary.avg_groundedness||1)*100) : 100;

  return (
    <div style={{padding:"32px 36px",maxWidth:1100,margin:"0 auto"}}>
      <div style={{display:"flex",justifyContent:"space-between",
        alignItems:"flex-start",marginBottom:24}}>
        <div>
          <h1 style={{fontSize:22,fontWeight:800,color:C.heading,marginBottom:4}}>
            AI Observability
          </h1>
          <p style={{fontSize:13,color:C.muted}}>
            LLM performance, cost, quality and guardrail metrics
          </p>
        </div>
        <select value={days} onChange={e=>setDays(Number(e.target.value))}
          style={{padding:"8px 12px",border:`1px solid ${C.border}`,
            borderRadius:8,fontSize:13,background:C.surface}}>
          {[7,14,30,60,90].map(d=>(
            <option key={d} value={d}>Last {d} days</option>
          ))}
        </select>
      </div>

      {summary && (
        <>
          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:16}}>
            <MetricCard Icon={Zap}        label="Total LLM Calls"
              value={(summary.total_calls||0).toLocaleString()}
              sub={`${summary.judge_calls||0} judge calls`}
              color={C.primary} bg={C.primaryLight}/>
            <MetricCard Icon={DollarSign} label="AI Spend"
              value={`$${(summary.total_cost_usd||0).toFixed(4)}`}
              sub={`${(summary.total_tokens||0).toLocaleString()} tokens`}
              color="#22C55E" bg="#F0FDF4"/>
            <MetricCard Icon={Clock}      label="Avg Latency"
              value={`${summary.avg_latency_ms||0}ms`}
              sub={`P95: ${summary.p95_latency_ms||0}ms`}
              color={(summary.p95_latency_ms||0)>3000?C.error:C.warning}
              bg={(summary.p95_latency_ms||0)>3000?"#FEF2F2":"#FFFBEB"}/>
            <MetricCard Icon={CheckCircle} label="Avg Groundedness"
              value={`${groundPct}%`}
              sub={`${summary.hallucination_count||0} hallucinations`}
              color={groundPct>=90?C.success:C.warning}
              bg={groundPct>=90?"#F0FDF4":"#FFFBEB"}/>
          </div>

          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:20}}>
            {[
              {label:"Hallucination Rate",  value:`${hallRate}%`,
               sub:"Target: <2%",
               color:hallRate>5?C.error:hallRate>2?C.warning:C.success,pct:hallRate},
              {label:"Cache Hit Rate",      value:`${cacheRate}%`,
               sub:"Target: >70%",
               color:cacheRate>70?C.success:C.warning,pct:cacheRate},
              {label:"Injections Detected", value:`${summary.injections_detected||0}`,
               sub:`${summary.safety_blocks||0} safety blocks`,
               color:(summary.injections_detected||0)>0?C.error:C.success,pct:0},
              {label:"User Satisfaction",   value:feedback?`${Math.round((feedback.satisfaction_rate||0)*100)}%`:"—",
               sub:`${feedback?.total_rated||0} rated`,
               color:C.success,pct:Math.round((feedback?.satisfaction_rate||0)*100)},
            ].map(m=>(
              <div key={m.label} style={{background:C.surface,
                border:`1px solid ${C.border}`,borderRadius:12,padding:"16px 20px"}}>
                <div style={{fontSize:12,color:C.muted,fontWeight:500,marginBottom:6}}>
                  {m.label}
                </div>
                <div style={{fontSize:22,fontWeight:900,color:m.color,marginBottom:6}}>
                  {m.value}
                </div>
                {m.pct > 0 && <MiniBar pct={m.pct} color={m.color}/>}
                <div style={{fontSize:10,color:C.muted,marginTop:4}}>{m.sub}</div>
              </div>
            ))}
          </div>
        </>
      )}

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:20}}>
        {/* By role */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{padding:"14px 20px",borderBottom:`1px solid ${C.border}`,
            fontSize:14,fontWeight:700,color:C.heading}}>Cost by Agent Role</div>
          {byRole.length===0 ? (
            <div style={{padding:32,textAlign:"center",color:C.muted,fontSize:13}}>
              No data yet — make some AI Copilot queries to see metrics
            </div>
          ) : byRole.map((r:any)=>(
            <div key={r.role} style={{display:"flex",alignItems:"center",
              gap:12,padding:"12px 20px",borderBottom:`1px solid ${C.border}`}}>
              <div style={{flex:1}}>
                <div style={{fontSize:12,fontWeight:700,color:C.heading,
                  textTransform:"capitalize",marginBottom:2}}>
                  {r.role.replace("_"," ")}
                </div>
                <div style={{fontSize:10,color:C.muted}}>
                  {r.calls} calls · {(r.tokens||0).toLocaleString()} tokens
                </div>
              </div>
              <div style={{textAlign:"right"}}>
                <div style={{fontSize:13,fontWeight:700,color:C.primary}}>
                  ${(r.cost_usd||0).toFixed(4)}
                </div>
                <div style={{fontSize:10,color:C.muted}}>{r.avg_latency_ms}ms avg</div>
              </div>
            </div>
          ))}
        </div>

        {/* Latency trend */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{padding:"14px 20px",borderBottom:`1px solid ${C.border}`,
            fontSize:14,fontWeight:700,color:C.heading}}>Daily Latency Trend</div>
          <div style={{padding:"12px 20px"}}>
            {trend.length===0 ? (
              <div style={{padding:24,textAlign:"center",color:C.muted,fontSize:13}}>
                No data yet
              </div>
            ) : trend.slice(0,7).map((t:any)=>(
              <div key={t.day} style={{marginBottom:12}}>
                <div style={{display:"flex",justifyContent:"space-between",
                  fontSize:11,marginBottom:4}}>
                  <span style={{color:C.muted}}>{t.day}</span>
                  <span style={{color:C.heading,fontWeight:600}}>
                    P50:{t.p50_ms}ms P95:{t.p95_ms}ms
                  </span>
                </div>
                <MiniBar pct={(t.p95_ms/5000)*100}
                  color={t.p95_ms>3000?C.error:t.p95_ms>1500?C.warning:C.success}/>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Canary */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,
        borderRadius:12,padding:"16px 20px",
        display:"flex",justifyContent:"space-between",alignItems:"center"}}>
        <div>
          <div style={{fontSize:14,fontWeight:700,color:C.heading,marginBottom:2}}>
            Model Degradation Canary
          </div>
          <div style={{fontSize:12,color:C.muted}}>
            5 test cases · runs weekly · alerts if accuracy drops below 90%
          </div>
        </div>
        <button
          onClick={async()=>{
            const r = await fetch(`${API}/api/v1/canary/run`,{
              method:"POST",headers:{Authorization:`Bearer ${getToken()}`}});
            const d = await r.json();
            const status = d.status || (d.below_threshold ? 'DEGRADED' : 'HEALTHY');
            const acc = d.accuracy !== undefined ? `${Math.round(d.accuracy * 100)}%` : 'N/A';
            const passed = d.passed ?? '?';
            const total = d.total ?? '?';
            const failed = d.failed > 0 ? `\nFailed: ${d.cases?.filter((c:any)=>!c.passed).map((c:any)=>c.id).join(', ')}` : '';
            alert(`Canary: ${status}\nAccuracy: ${acc} (${passed}/${total} passed)${failed}`);
          }}
          style={{padding:"8px 16px",background:C.primary,color:"white",
            borderRadius:8,fontSize:12,fontWeight:700,border:"none",cursor:"pointer"}}>
          Run Now
        </button>
      </div>
    </div>
  );
}
