"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { contracts as contractsAPI, billing as billingAPI, getToken, Contract } from "@/lib/api";

const API = "http://localhost:8000";

const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF", primaryDark:"#4338CA",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  success:"#22C55E", successLight:"#F0FDF4",
  warning:"#F59E0B", warningLight:"#FFFBEB",
  error:"#EF4444", errorLight:"#FEF2F2",
};

const RISK_COLORS: Record<string,{bg:string,text:string,dot:string}> = {
  high:   {bg:"#FEF2F2",text:"#DC2626",dot:"#EF4444"},
  medium: {bg:"#FFFBEB",text:"#D97706",dot:"#F59E0B"},
  low:    {bg:"#F0FDF4",text:"#16A34A",dot:"#22C55E"},
};

function getTimeOfDay() {
  const h = new Date().getHours();
  return h < 12 ? "morning" : h < 17 ? "afternoon" : "evening";
}

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color=C.primary, icon, trend }:{
  label:string; value:string|number; sub?:string;
  color?:string; icon:string; trend?:{value:number,label:string};
}) {
  return (
    <div style={{background:C.surface,border:`1px solid ${C.border}`,
      borderRadius:16,padding:"20px 24px",
      boxShadow:"0 1px 3px rgba(0,0,0,0.06)"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
        <div style={{fontSize:13,color:C.muted,fontWeight:500,marginBottom:12}}>{label}</div>
        <span style={{fontSize:22}}>{icon}</span>
      </div>
      <div style={{fontSize:32,fontWeight:800,color,letterSpacing:"-0.02em",marginBottom:4}}>
        {value}
      </div>
      <div style={{display:"flex",alignItems:"center",gap:8}}>
        {sub && <div style={{fontSize:12,color:C.muted}}>{sub}</div>}
        {trend && (
          <span style={{fontSize:11,fontWeight:600,
            color:trend.value>0?C.success:C.error,
            background:trend.value>0?C.successLight:C.errorLight,
            padding:"1px 6px",borderRadius:20}}>
            {trend.value>0?"↑":"↓"} {Math.abs(trend.value)}% {trend.label}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Risk Donut Chart ─────────────────────────────────────────────────────────
function RiskDonut({ high,medium,low,total }:{high:number,medium:number,low:number,total:number}) {
  const size = 140;
  const cx = size/2, cy = size/2, r = 52, stroke = 18;
  const circumference = 2 * Math.PI * r;

  const segments = [
    {count:high,   color:"#EF4444", label:"High"},
    {count:medium, color:"#F59E0B", label:"Medium"},
    {count:low,    color:"#22C55E", label:"Low"},
  ].filter(s=>s.count>0);

  let offset = 0;
  const slices = segments.map(seg=>{
    const pct = total > 0 ? seg.count/total : 0;
    const dash = pct * circumference;
    const gap  = circumference - dash;
    const slice = {
      ...seg, pct,
      dashArray:`${dash} ${gap}`,
      dashOffset: -offset * circumference / 1,
      rotation: offset * 360,
    };
    offset += pct;
    return slice;
  });

  return (
    <div style={{position:"relative",width:size,height:size,flexShrink:0}}>
      <svg width={size} height={size} style={{transform:"rotate(-90deg)"}}>
        {total === 0 ? (
          <circle cx={cx} cy={cy} r={r} fill="none"
            stroke={C.border} strokeWidth={stroke}/>
        ) : slices.map((s,i)=>(
          <circle key={i} cx={cx} cy={cy} r={r} fill="none"
            stroke={s.color} strokeWidth={stroke}
            strokeDasharray={s.dashArray}
            strokeDashoffset={0}
            style={{transition:"stroke-dasharray 0.5s ease"}}
            transform={`rotate(${s.rotation} ${cx} ${cy})`}/>
        ))}
        {/* Inner white circle */}
        <circle cx={cx} cy={cy} r={r-stroke/2-2} fill="white"/>
      </svg>
      {/* Center label */}
      <div style={{position:"absolute",inset:0,display:"flex",
        flexDirection:"column",alignItems:"center",justifyContent:"center"}}>
        <div style={{fontSize:24,fontWeight:800,color:C.heading}}>{total}</div>
        <div style={{fontSize:10,color:C.muted,fontWeight:500}}>contracts</div>
      </div>
    </div>
  );
}

// ─── Mini Progress Bar ────────────────────────────────────────────────────────
function MiniBar({value,max,color}:{value:number,max:number,color:string}) {
  const pct = max > 0 ? Math.min(100, (value/max)*100) : 0;
  return (
    <div style={{height:6,background:C.border,borderRadius:3,overflow:"hidden",flex:1}}>
      <div style={{height:"100%",width:`${pct}%`,background:color,
        borderRadius:3,transition:"width 0.5s ease"}}/>
    </div>
  );
}

// ─── Section Header ───────────────────────────────────────────────────────────
function SectionHeader({title,sub,action,actionHref}:{
  title:string;sub?:string;action?:string;actionHref?:string;
}) {
  return (
    <div style={{display:"flex",justifyContent:"space-between",
      alignItems:"center",marginBottom:16}}>
      <div>
        <h2 style={{fontSize:16,fontWeight:700,color:C.heading,margin:0}}>{title}</h2>
        {sub && <p style={{fontSize:13,color:C.muted,margin:"2px 0 0"}}>{sub}</p>}
      </div>
      {action && actionHref && (
        <Link href={actionHref}
          style={{fontSize:13,fontWeight:600,color:C.primary,textDecoration:"none",
            padding:"6px 14px",background:C.primaryLight,borderRadius:8}}>
          {action}
        </Link>
      )}
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { user } = useAuthStore();
  const router = useRouter();

  const [recentContracts, setRecentContracts] = useState<Contract[]>([]);
  const [allContracts, setAllContracts]       = useState<Contract[]>([]);
  const [obligations, setObligations]         = useState<any[]>([]);
  const [reviews, setReviews]                 = useState<any[]>([]);
  const [insights, setInsights]               = useState<string[]>([]);
  const [usage, setUsage]                     = useState<any>(null);
  const [loading, setLoading]                 = useState(true);

  useEffect(() => {
    const token = getToken();
    const h = {Authorization:`Bearer ${token}`};

    const load = async () => {
      try {
        const [contractsData, usageData, obligationsData, reviewsData] = await Promise.all([
          contractsAPI.list({page:1, page_size:100}),
          billingAPI.usage(),
          fetch(`${API}/api/v1/obligations/?page_size=50`,{headers:h}).then(r=>r.json()),
          fetch(`${API}/api/v1/reviews/`,{headers:h}).then(r=>r.json()),
        ]);
        const allC = contractsData.contracts || [];
        setAllContracts(allC);
        setRecentContracts(allC.slice(0,5));
        setUsage(usageData.usage);
        setObligations(obligationsData.obligations || []);
        setReviews(reviewsData.reviews || []);

        // Generate AI insights
        const high = allC.filter((c:any)=>c.risk_level==="high").length;
        const ins: string[] = [];
        const expiring = allC.filter((c:any)=>{
          if (!c.expiry_date) return false;
          const days = Math.ceil((new Date(c.expiry_date).getTime()-Date.now())/(1000*60*60*24));
          return days > 0 && days <= 30;
        });
        if (expiring.length > 0) {
          const val = expiring.reduce((s:number,c:any)=>s+(c.contract_value||0),0);
          ins.push(`${expiring.length} contract${expiring.length>1?"s":""} expiring within 30 days${val>0?` worth ₹${(val/100000).toFixed(1)}L`:""}`);
        }
        if (high > 0) ins.push(`${high} high-risk contract${high>1?"s":""} require immediate attention`);
        const pendingReviews = (reviewsData.reviews||[]).filter((r:any)=>r.status==="pending"||r.status==="in_review");
        if (pendingReviews.length > 0) ins.push(`${pendingReviews.length} contract${pendingReviews.length>1?"s":""} awaiting legal review`);
        const overdueObs = (obligationsData.obligations||[]).filter((o:any)=>{
          if (!o.due_date || o.status==="completed") return false;
          return new Date(o.due_date) < new Date();
        });
        if (overdueObs.length > 0) ins.push(`${overdueObs.length} overdue obligation${overdueObs.length>1?"s":""} need attention`);
        setInsights(ins);
      } catch(e) { console.error(e); }
      finally { setLoading(false); }
    };
    load();
  }, []);

  // Computed stats
  const stats = useMemo(()=>({
    total:     allContracts.length,
    high:      allContracts.filter(c=>c.risk_level==="high").length,
    medium:    allContracts.filter(c=>c.risk_level==="medium").length,
    low:       allContracts.filter(c=>c.risk_level==="low").length,
    analyzed:  allContracts.filter(c=>c.status==="analyzed").length,
    pending:   allContracts.filter(c=>["queued","parsing","extracting","scoring","indexing"].includes(c.status)).length,
  }), [allContracts]);

  // Counterparty grouping for risk widget
  const counterpartyRisk = useMemo(()=>{
    const map: Record<string,{high:number,medium:number,low:number,total:number}> = {};
    allContracts.forEach(c=>{
      const cp = c.counterparty || "Unknown";
      if (!map[cp]) map[cp] = {high:0,medium:0,low:0,total:0};
      map[cp].total++;
      if (c.risk_level) map[cp][c.risk_level as "high"|"medium"|"low"]++;
    });
    return Object.entries(map)
      .sort((a,b)=>b[1].high-a[1].high||b[1].total-a[1].total)
      .slice(0,6);
  }, [allContracts]);

  // Due obligations
  const dueOblications = useMemo(()=>
    obligations
      .filter(o=>o.due_date && o.status!=="completed")
      .sort((a,b)=>new Date(a.due_date).getTime()-new Date(b.due_date).getTime())
      .slice(0,5)
  , [obligations]);

  // Review pipeline
  const reviewPipeline = useMemo(()=>{
    const pending   = reviews.filter(r=>r.status==="pending").length;
    const inReview  = reviews.filter(r=>r.status==="in_review").length;
    const approved  = reviews.filter(r=>r.status==="approved").length;
    const rejected  = reviews.filter(r=>r.status==="rejected").length;
    return {pending, inReview, approved, rejected, total:reviews.length};
  }, [reviews]);

  if (loading) return (
    <div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"60vh"}}>
      <div style={{textAlign:"center"}}>
        <div style={{fontSize:32,marginBottom:12}}>⚡</div>
        <div style={{fontSize:14,color:C.muted}}>Loading dashboard...</div>
      </div>
    </div>
  );

  return (
    <div style={{padding:"32px 36px",maxWidth:1400,margin:"0 auto"}}>

      {/* ── Upgrade Banner ──────────────────────────────────────────────── */}
      {user?.plan==="free" && (
        <div style={{marginBottom:20,padding:"14px 20px",borderRadius:12,
          background:"linear-gradient(135deg,#0A1128,#0A1F4A)",
          border:"1px solid rgba(0,102,255,0.3)",
          display:"flex",alignItems:"center",gap:16,flexWrap:"wrap"}}>
          <div style={{fontSize:24}}>⚡</div>
          <div style={{flex:1,minWidth:200}}>
            <div style={{fontSize:14,fontWeight:700,color:"white",marginBottom:2}}>
              You're on the Free plan — unlock the full Claustor experience
            </div>
            <div style={{fontSize:12,color:"rgba(255,255,255,0.5)"}}>
              Review workflows · Team management · Obligations tracking ·
              Audit log · Playbook similarity · 10× faster processing
            </div>
          </div>
          <div style={{display:"flex",gap:8,flexShrink:0}}>
            <Link href="/dashboard/admin/billing"
              style={{padding:"9px 18px",background:"#0066FF",color:"white",
                borderRadius:8,fontSize:13,fontWeight:700,textDecoration:"none",
                boxShadow:"0 2px 8px rgba(0,102,255,0.4)",whiteSpace:"nowrap"}}>
              Upgrade to Starter ₹3,999/mo →
            </Link>
            <Link href="/dashboard/admin/billing"
              style={{padding:"9px 14px",background:"rgba(255,255,255,0.08)",
                color:"rgba(255,255,255,0.7)",borderRadius:8,fontSize:13,
                fontWeight:600,textDecoration:"none",whiteSpace:"nowrap"}}>
              See all plans
            </Link>
          </div>
        </div>
      )}
      {user?.plan==="starter" && (
        <div style={{marginBottom:20,padding:"14px 20px",borderRadius:12,
          background:"linear-gradient(135deg,#1a0533,#0A1128)",
          border:"1px solid rgba(139,92,246,0.3)",
          display:"flex",alignItems:"center",gap:16,flexWrap:"wrap"}}>
          <div style={{fontSize:24}}>🚀</div>
          <div style={{flex:1,minWidth:200}}>
            <div style={{fontSize:14,fontWeight:700,color:"white",marginBottom:2}}>
              Unlock Professional — the full AI contract intelligence platform
            </div>
            <div style={{fontSize:12,color:"rgba(255,255,255,0.5)"}}>
              PII masking · Dedicated processing queue · 1,000 contracts ·
              Playbook similarity · Industry risk weights · Full audit trail
            </div>
          </div>
          <div style={{display:"flex",gap:8,flexShrink:0}}>
            <Link href="/dashboard/admin/billing"
              style={{padding:"9px 18px",background:"#7C3AED",color:"white",
                borderRadius:8,fontSize:13,fontWeight:700,textDecoration:"none",
                boxShadow:"0 2px 8px rgba(124,58,237,0.4)",whiteSpace:"nowrap"}}>
              Upgrade to Pro ₹16,499/mo →
            </Link>
            <Link href="/dashboard/admin/billing"
              style={{padding:"9px 14px",background:"rgba(255,255,255,0.08)",
                color:"rgba(255,255,255,0.7)",borderRadius:8,fontSize:13,
                fontWeight:600,textDecoration:"none",whiteSpace:"nowrap"}}>
              Compare plans
            </Link>
          </div>
        </div>
      )}

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div style={{marginBottom:28}}>
        <h1 style={{fontSize:26,fontWeight:800,color:C.heading,marginBottom:4}}>
          Good {getTimeOfDay()}, {user?.email?.split("@")[0]} 👋
        </h1>
        <p style={{fontSize:14,color:C.muted}}>
          Here's your contract intelligence overview for today.
        </p>
      </div>

      {/* ── AI Insights Banner ────────────────────────────────────────────── */}
      {insights.length > 0 && (
        <div style={{background:`linear-gradient(135deg, ${C.primary}08, ${C.primaryLight})`,
          border:`1px solid ${C.primary}30`,borderRadius:16,padding:"16px 20px",
          marginBottom:28}}>
          <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
            <span style={{fontSize:18}}>💡</span>
            <span style={{fontSize:13,fontWeight:700,color:C.primary,textTransform:"uppercase",
              letterSpacing:"0.05em"}}>AI Insights</span>
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:6}}>
            {insights.map((ins,i)=>(
              <div key={i} style={{display:"flex",alignItems:"center",gap:8,
                fontSize:13,color:C.body}}>
                <span style={{width:6,height:6,borderRadius:"50%",
                  background:C.primary,flexShrink:0,display:"inline-block"}}/>
                {ins}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Stats Grid ───────────────────────────────────────────────────── */}
      <div style={{display:"grid",
        gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",
        gap:16,marginBottom:28}}>
        <StatCard label="Total Contracts"    value={stats.total}    icon="📄" color={C.primary}
          sub={`${stats.analyzed} analyzed`}/>
        <StatCard label="High Risk"          value={stats.high}     icon="🔴" color={C.error}
          sub="Requires attention"/>
        <StatCard label="Pending Reviews"    value={reviewPipeline.pending+reviewPipeline.inReview}
          icon="📋" color={C.warning} sub="Awaiting decision"/>
        <StatCard label="Due Obligations"    value={dueOblications.length}
          icon="⏰" color={dueOblications.length>0?C.error:C.success}
          sub="Within 30 days"/>
        <StatCard label="Contracts Analysed" value={usage?.contracts?.used??0}
          icon="🤖" color={C.primary}
          sub={`of ${usage?.contracts?.limit??0} this month`}/>
        <StatCard label="AI Queries"         value={usage?.queries?.used??0}
          icon="💬" color={C.primaryDark}
          sub={`of ${usage?.queries?.limit??0} this month`}/>
      </div>

      {/* ── Row 2: Risk Distribution + Review Pipeline ────────────────────── */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:20,marginBottom:20}}>

        {/* Risk Distribution Widget */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:16,padding:"20px 24px",
          boxShadow:"0 1px 3px rgba(0,0,0,0.06)"}}>
          <SectionHeader title="📊 Risk Distribution"
            sub="By counterparty" action="View all" actionHref="/dashboard/contracts"/>
          <div style={{display:"flex",gap:24,alignItems:"flex-start"}}>
            {/* Donut */}
            <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:12}}>
              <RiskDonut high={stats.high} medium={stats.medium}
                low={stats.low} total={stats.total}/>
              {/* Legend */}
              <div style={{display:"flex",flexDirection:"column",gap:6,width:"100%"}}>
                {[
                  {label:"High",   count:stats.high,   color:"#EF4444"},
                  {label:"Medium", count:stats.medium, color:"#F59E0B"},
                  {label:"Low",    count:stats.low,    color:"#22C55E"},
                ].map(({label,count,color})=>(
                  <div key={label} style={{display:"flex",alignItems:"center",gap:8}}>
                    <div style={{width:10,height:10,borderRadius:2,background:color,flexShrink:0}}/>
                    <span style={{fontSize:12,color:C.body,flex:1}}>{label}</span>
                    <span style={{fontSize:12,fontWeight:700,color:C.heading}}>{count}</span>
                    <span style={{fontSize:11,color:C.muted,minWidth:30,textAlign:"right"}}>
                      {stats.total>0?Math.round(count/stats.total*100):0}%
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Counterparty list */}
            <div style={{flex:1,minWidth:0}}>
              <div style={{fontSize:11,fontWeight:700,color:C.muted,
                textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:10}}>
                Counterparty Activity
              </div>
              {counterpartyRisk.length===0 ? (
                <div style={{fontSize:13,color:C.muted,textAlign:"center",padding:20}}>
                  No contracts yet
                </div>
              ) : counterpartyRisk.map(([cp,risk])=>{
                const topRisk = risk.high>0?"high":risk.medium>0?"medium":"low";
                const rc = RISK_COLORS[topRisk];
                return (
                  <div key={cp} style={{display:"flex",alignItems:"center",gap:8,
                    padding:"7px 10px",marginBottom:4,borderRadius:8,
                    background:`${rc.dot}08`,border:`1px solid ${rc.dot}20`}}>
                    <span style={{width:8,height:8,borderRadius:"50%",
                      background:rc.dot,flexShrink:0}}/>
                    <span style={{fontSize:12,color:C.body,flex:1,
                      overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                      {cp}
                    </span>
                    <span style={{fontSize:11,fontWeight:700,color:rc.text,
                      background:rc.bg,padding:"1px 6px",borderRadius:20,flexShrink:0}}>
                      {risk.total} {topRisk==="high"?"🔴":topRisk==="medium"?"🟡":"🟢"}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Review Pipeline */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:16,padding:"20px 24px",
          boxShadow:"0 1px 3px rgba(0,0,0,0.06)"}}>
          <SectionHeader title="📋 Review Pipeline"
            sub={`${reviewPipeline.total} total reviews`}
            action="View all" actionHref="/dashboard/reviews"/>
          <div style={{display:"flex",flexDirection:"column",gap:14}}>
            {[
              {label:"Pending",    count:reviewPipeline.pending,   color:"#F59E0B",icon:"⏳"},
              {label:"In Review",  count:reviewPipeline.inReview,  color:"#3B82F6",icon:"🔍"},
              {label:"Approved",   count:reviewPipeline.approved,  color:"#22C55E",icon:"✅"},
              {label:"Rejected",   count:reviewPipeline.rejected,  color:"#EF4444",icon:"❌"},
            ].map(({label,count,color,icon})=>(
              <div key={label}>
                <div style={{display:"flex",justifyContent:"space-between",
                  alignItems:"center",marginBottom:6}}>
                  <div style={{display:"flex",alignItems:"center",gap:6}}>
                    <span style={{fontSize:14}}>{icon}</span>
                    <span style={{fontSize:13,color:C.body,fontWeight:500}}>{label}</span>
                  </div>
                  <span style={{fontSize:13,fontWeight:700,color:C.heading}}>{count}</span>
                </div>
                <MiniBar value={count} max={Math.max(reviewPipeline.total,1)} color={color}/>
              </div>
            ))}
          </div>

          {/* Recent reviews */}
          {reviews.slice(0,3).length > 0 && (
            <div style={{marginTop:16,borderTop:`1px solid ${C.border}`,paddingTop:12}}>
              <div style={{fontSize:11,fontWeight:700,color:C.muted,
                textTransform:"uppercase",marginBottom:8}}>Recent</div>
              {reviews.slice(0,3).map((r:any)=>(
                <div key={r.id}
                  onClick={()=>router.push(`/dashboard/reviews/${r.id}`)}
                  style={{display:"flex",alignItems:"center",gap:8,
                    padding:"6px 0",cursor:"pointer",borderBottom:`1px solid ${C.border}`}}>
                  <span style={{fontSize:12,color:C.body,flex:1,
                    overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                    {r.contract_title||"Contract"}
                  </span>
                  <span style={{fontSize:11,padding:"1px 6px",borderRadius:20,fontWeight:600,
                    background:r.status==="approved"?C.successLight:
                               r.status==="rejected"?C.errorLight:C.warningLight,
                    color:r.status==="approved"?C.success:
                          r.status==="rejected"?C.error:C.warning}}>
                    {r.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Row 3: Obligations Due + Recent Contracts ─────────────────────── */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1.5fr",gap:20,marginBottom:20}}>

        {/* Obligations Due Soon */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:16,padding:"20px 24px",
          boxShadow:"0 1px 3px rgba(0,0,0,0.06)"}}>
          <SectionHeader title="⏰ Obligations Due"
            sub="Upcoming deadlines" action="View all" actionHref="/dashboard/obligations"/>
          {dueOblications.length===0 ? (
            <div style={{padding:"32px 0",textAlign:"center"}}>
              <div style={{fontSize:32,marginBottom:8}}>✅</div>
              <div style={{fontSize:13,color:C.muted}}>No upcoming obligations</div>
            </div>
          ) : dueOblications.map(o=>{
            const daysLeft = Math.ceil((new Date(o.due_date).getTime()-Date.now())/(1000*60*60*24));
            const urgent = daysLeft <= 7;
            const overdue = daysLeft < 0;
            return (
              <div key={o.id} style={{display:"flex",alignItems:"flex-start",gap:12,
                padding:"10px 12px",marginBottom:6,borderRadius:10,
                background:overdue?C.errorLight:urgent?C.warningLight:C.bg,
                border:`1px solid ${overdue?C.error+"30":urgent?C.warning+"30":C.border}`}}>
                <span style={{fontSize:18,flexShrink:0}}>
                  {overdue?"🚨":urgent?"⚠️":"📌"}
                </span>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontSize:13,fontWeight:600,color:C.heading,
                    overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                    {o.title||o.obligation_type}
                  </div>
                  <div style={{fontSize:11,color:C.muted,marginTop:2}}>
                    {o.party||"—"}
                  </div>
                </div>
                <div style={{textAlign:"right",flexShrink:0}}>
                  <div style={{fontSize:12,fontWeight:700,
                    color:overdue?C.error:urgent?C.warning:C.muted}}>
                    {overdue?`${Math.abs(daysLeft)}d overdue`:
                     daysLeft===0?"Today":
                     daysLeft===1?"Tomorrow":`${daysLeft}d`}
                  </div>
                  <div style={{fontSize:10,color:C.muted}}>
                    {new Date(o.due_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short"})}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Recent Contracts */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:16,padding:"20px 24px",
          boxShadow:"0 1px 3px rgba(0,0,0,0.06)"}}>
          <SectionHeader title="📄 Recent Contracts"
            sub={`${stats.total} total`} action="View all" actionHref="/dashboard/contracts"/>
          {recentContracts.length===0 ? (
            <div style={{padding:"32px 0",textAlign:"center"}}>
              <div style={{fontSize:40,marginBottom:8}}>📭</div>
              <div style={{fontSize:14,fontWeight:600,color:C.heading,marginBottom:4}}>
                No contracts yet
              </div>
              <div style={{fontSize:13,color:C.muted,marginBottom:16}}>
                Upload your first contract to get started
              </div>
              <Link href="/dashboard/contracts"
                style={{padding:"8px 20px",background:C.primary,color:"white",
                  borderRadius:8,fontSize:13,fontWeight:600,textDecoration:"none"}}>
                Upload Contract
              </Link>
            </div>
          ) : (
            <div>
              {recentContracts.map(c=>{
                const rc = RISK_COLORS[c.risk_level||"low"];
                return (
                  <div key={c.id}
                    onClick={()=>router.push(`/dashboard/contracts/${c.id}`)}
                    style={{display:"flex",alignItems:"center",gap:12,
                      padding:"10px 12px",marginBottom:6,borderRadius:10,
                      cursor:"pointer",border:`1px solid ${C.border}`,
                      background:C.bg,transition:"all 0.15s"}}
                    onMouseEnter={e=>(e.currentTarget.style.borderColor=C.primary)}
                    onMouseLeave={e=>(e.currentTarget.style.borderColor=C.border)}>
                    {/* Risk dot */}
                    <div style={{width:10,height:10,borderRadius:"50%",
                      background:rc.dot,flexShrink:0}}/>
                    {/* Title */}
                    <div style={{flex:1,minWidth:0}}>
                      <div style={{fontSize:13,fontWeight:600,color:C.heading,
                        overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                        {c.title}
                      </div>
                      <div style={{fontSize:11,color:C.muted}}>
                        {c.counterparty||"—"} · {c.contract_type||"Contract"}
                      </div>
                    </div>
                    {/* Value */}
                    {c.contract_value && (
                      <div style={{fontSize:12,fontWeight:600,color:C.body,
                        flexShrink:0,textAlign:"right"}}>
                        {c.contract_currency||"₹"}
                        {(c.contract_value/100000).toFixed(1)}L
                      </div>
                    )}
                    {/* Status */}
                    <span style={{fontSize:11,fontWeight:600,padding:"2px 8px",
                      borderRadius:20,flexShrink:0,
                      background:c.status==="analyzed"?C.successLight:"#F3F4F6",
                      color:c.status==="analyzed"?C.success:C.muted}}>
                      {c.status==="analyzed"?"✓ Done":c.status}
                    </span>
                  </div>
                );
              })}
              <div style={{textAlign:"center",marginTop:8}}>
                <Link href="/dashboard/contracts"
                  style={{fontSize:13,fontWeight:600,color:C.primary,textDecoration:"none"}}>
                  View all {stats.total} contracts →
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Usage Bar ─────────────────────────────────────────────────────── */}
      {usage && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:16,padding:"20px 24px",
          boxShadow:"0 1px 3px rgba(0,0,0,0.06)"}}>
          <SectionHeader title="📈 Monthly Usage" sub="Plan consumption"/>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:24}}>
            {[
              {label:"Contract Analyses",icon:"📄",used:usage.contracts?.used??0,limit:usage.contracts?.limit??0},
              {label:"AI Queries",       icon:"💬",used:usage.queries?.used??0,  limit:usage.queries?.limit??0},
            ].map(({label,icon,used,limit})=>{
              const pct = limit>0?Math.min(100,Math.round(used/limit*100)):0;
              const color = pct>80?C.error:pct>60?C.warning:C.primary;
              return (
                <div key={label}>
                  <div style={{display:"flex",justifyContent:"space-between",
                    alignItems:"center",marginBottom:8}}>
                    <div style={{display:"flex",alignItems:"center",gap:6}}>
                      <span>{icon}</span>
                      <span style={{fontSize:13,color:C.body,fontWeight:500}}>{label}</span>
                    </div>
                    <span style={{fontSize:13,fontWeight:700,color}}>
                      {used}/{limit} <span style={{fontSize:11,color:C.muted}}>({pct}%)</span>
                    </span>
                  </div>
                  <div style={{height:8,background:C.border,borderRadius:4,overflow:"hidden"}}>
                    <div style={{height:"100%",width:`${pct}%`,background:color,
                      borderRadius:4,transition:"width 0.5s ease"}}/>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin{to{transform:rotate(360deg)}}
      `}</style>
    </div>
  );
}
