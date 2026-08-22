"use client";
export const dynamic = "force-dynamic";
import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { contracts as contractsAPI, billing as billingAPI, getToken } from "@/lib/api";
import { Contract } from "@/lib/api";
import {
  FileText, AlertTriangle, ClipboardList, Clock,
  Zap, ArrowRight, ChevronRight,
  CheckCircle, XCircle, RotateCcw, Eye,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const C = {
  primary:"#0066FF", primaryLight:"#EFF6FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#F8FAFC",
  success:"#22C55E", warning:"#F59E0B", error:"#EF4444",
  navy:"#0A1128",
};

// ── Helpers ───────────────────────────────────────────────────────
const fmtValue = (v: number) =>
  v >= 10000000 ? `₹${(v/10000000).toFixed(1)}Cr`
  : v >= 100000 ? `₹${(v/100000).toFixed(1)}L`
  : v > 0       ? `₹${v.toLocaleString()}` : "—";

function getGreeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

// ── Shared ProgressBar ────────────────────────────────────────────
function ProgressBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div style={{height:4,background:C.border,borderRadius:2,marginTop:8,overflow:"hidden"}}>
      <div style={{height:"100%",width:`${Math.min(pct,100)}%`,
        background:color,borderRadius:2,transition:"width 0.6s"}}/>
    </div>
  );
}

// ── StatusBadge ───────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string,{label:string;color:string;bg:string}> = {
    analyzed:   {label:"Active",          color:"#16A34A",bg:"#F0FDF4"},
    approved:   {label:"Approved",        color:"#16A34A",bg:"#F0FDF4"},
    in_review:  {label:"Under Review",    color:"#D97706",bg:"#FFFBEB"},
    pending:    {label:"Pending Review",  color:"#9333EA",bg:"#FAF5FF"},
    rejected:   {label:"Needs Revision",  color:"#DC2626",bg:"#FEF2F2"},
    queued:     {label:"Processing",      color:C.primary,bg:C.primaryLight},
    scoring:    {label:"Processing",      color:C.primary,bg:C.primaryLight},
    extracting: {label:"Processing",      color:C.primary,bg:C.primaryLight},
    failed:     {label:"Failed",          color:"#DC2626",bg:"#FEF2F2"},
  };
  const s = cfg[status] || {label:status, color:C.muted, bg:C.bg};
  return (
    <span style={{fontSize:10,fontWeight:700,padding:"2px 8px",borderRadius:20,
      color:s.color,background:s.bg,whiteSpace:"nowrap"}}>
      {s.label}
    </span>
  );
}

// ── Donut Chart ───────────────────────────────────────────────────
function DonutChart({ high, medium, low, total, activeLevel, onHover }: {
  high:number; medium:number; low:number; total:number;
  activeLevel:string|null; onHover:(l:string|null)=>void;
}) {
  const size=140, cx=70, cy=70, r=52, sw=18;
  const segs = [
    {key:"high",  count:high,   color:C.error},
    {key:"medium",count:medium, color:C.warning},
    {key:"low",   count:low,    color:C.success},
  ];
  let angle = -90;
  const arcs = segs.map(s=>{
    const start=angle; angle+=total>0?(s.count/total)*360:0;
    return {...s,start,end:angle};
  });

  const pt=(a:number,rad:number)=>({
    x:cx+rad*Math.cos(a*Math.PI/180),
    y:cy+rad*Math.sin(a*Math.PI/180),
  });

  const arcD=(s:number,e:number,rad:number)=>{
    if(e-s<=1) return "";
    const g=2; const a=s+g/2, b=e-g/2;
    const S=pt(a,rad),E=pt(b,rad);
    return `M${S.x},${S.y}A${rad},${rad},0,${b-a>180?1:0},1,${E.x},${E.y}`;
  };

  const active = activeLevel ? arcs.find(a=>a.key===activeLevel) : null;

  if(total===0) return (
    <svg width={size} height={size} style={{display:"block",margin:"0 auto"}}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={C.border} strokeWidth={sw}/>
      <text x={cx} y={cy-5} textAnchor="middle" fontSize={20} fontWeight={900} fill={C.muted}>0</text>
      <text x={cx} y={cy+12} textAnchor="middle" fontSize={10} fill={C.muted}>Total</text>
    </svg>
  );

  return (
    <svg width={size} height={size} style={{display:"block",margin:"0 auto",cursor:"pointer"}}>
      {arcs.map(arc=>{
        if(!arc.count) return null;
        const isActive=activeLevel===arc.key;
        const isInactive=activeLevel&&!isActive;
        return (
          <path key={arc.key}
            d={arcD(arc.start,arc.end,isActive?r+4:r)}
            fill="none" stroke={arc.color}
            strokeWidth={isActive?sw+4:sw} strokeLinecap="round"
            opacity={isInactive?0.25:1}
            style={{transition:"all 0.2s"}}
            onMouseEnter={()=>onHover(arc.key)}
            onMouseLeave={()=>onHover(null)}
          />
        );
      })}
      <text x={cx} y={cy-5} textAnchor="middle"
        fontSize={active?18:22} fontWeight={900}
        fill={active?.color||C.heading} style={{transition:"all 0.2s"}}>
        {active?active.count:total}
      </text>
      <text x={cx} y={cy+12} textAnchor="middle" fontSize={10} fill={C.muted}>
        {active?active.key.charAt(0).toUpperCase()+active.key.slice(1):"Total"}
      </text>
    </svg>
  );
}

// ── Stacked Pipeline Bar ──────────────────────────────────────────
function PipelineFunnel({ pipeline, total }: {pipeline:Record<string,number>;total:number}) {
  const stages = [
    {key:"pending",            label:"Pending",   color:"#9333EA"},
    {key:"in_review",          label:"In Review", color:C.warning},
    {key:"approved",           label:"Approved",  color:C.success},
    {key:"rejected",           label:"Rejected",  color:C.error},
    {key:"revision_requested", label:"Revision",  color:"#F97316"},
  ].filter(s=>(pipeline[s.key]||0)>0);

  if(!total) return (
    <div style={{textAlign:"center",padding:"32px 0",color:C.muted,fontSize:12}}>
      No reviews in pipeline
    </div>
  );

  return (
    <div>
      <div style={{display:"flex",height:32,borderRadius:8,overflow:"hidden",gap:2,marginBottom:10}}>
        {stages.map(s=>{
          const pct=(pipeline[s.key]||0)/total*100;
          return (
            <div key={s.key} title={`${s.label}: ${pipeline[s.key]}`}
              style={{flex:pct,background:s.color,minWidth:pct>5?24:0,
                display:"flex",alignItems:"center",justifyContent:"center",
                fontSize:11,fontWeight:700,color:"white"}}>
              {pct>8?pipeline[s.key]:""}
            </div>
          );
        })}
      </div>
      <div style={{display:"flex",gap:10,flexWrap:"wrap"}}>
        {stages.map(s=>(
          <div key={s.key} style={{display:"flex",alignItems:"center",gap:4}}>
            <div style={{width:8,height:8,borderRadius:2,background:s.color}}/>
            <span style={{fontSize:11,color:C.muted}}>{s.label}</span>
            <span style={{fontSize:11,fontWeight:700,color:C.heading}}>{pipeline[s.key]||0}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Obligation Timeline ───────────────────────────────────────────
function ObligationTimeline({ obligations }: { obligations: any[] }) {
  const now = Date.now();
  const overdue  = obligations.filter(o=>new Date(o.due_date).getTime()<now).length;
  const thisWeek = obligations.filter(o=>{
    const d=(new Date(o.due_date).getTime()-now)/86400000;
    return d>=0&&d<=7;
  }).length;
  const later = obligations.filter(o=>{
    const d=(new Date(o.due_date).getTime()-now)/86400000;
    return d>7;
  }).length;
  const total=overdue+thisWeek+later;
  if(!total) return null;
  const segs=[
    {label:"Overdue",   count:overdue,  color:C.error},
    {label:"This week", count:thisWeek, color:C.warning},
    {label:"Later",     count:later,    color:C.muted},
  ].filter(s=>s.count>0);
  return (
    <div style={{marginBottom:10}}>
      <div style={{display:"flex",height:5,borderRadius:3,overflow:"hidden",gap:2,marginBottom:5}}>
        {segs.map(s=>(
          <div key={s.label} style={{flex:s.count,background:s.color,minWidth:4}}/>
        ))}
      </div>
      <div style={{display:"flex",gap:10}}>
        {segs.map(s=>(
          <div key={s.label} style={{display:"flex",alignItems:"center",gap:3}}>
            <div style={{width:6,height:6,borderRadius:1,background:s.color}}/>
            <span style={{fontSize:9,color:C.muted}}>{s.label}</span>
            <span style={{fontSize:9,fontWeight:700,color:s.color}}>{s.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Chart A: Value by Risk ────────────────────────────────────────
function ValueByRiskChart({ contracts }: { contracts: any[] }) {
  const data = [
    {label:"High Risk",   color:C.error,   value:contracts.filter(c=>c.risk_level==="high").reduce((s:number,c:any)=>s+(c.contract_value||0),0), count:contracts.filter(c=>c.risk_level==="high").length},
    {label:"Medium Risk", color:C.warning, value:contracts.filter(c=>c.risk_level==="medium").reduce((s:number,c:any)=>s+(c.contract_value||0),0), count:contracts.filter(c=>c.risk_level==="medium").length},
    {label:"Low Risk",    color:C.success, value:contracts.filter(c=>c.risk_level==="low").reduce((s:number,c:any)=>s+(c.contract_value||0),0), count:contracts.filter(c=>c.risk_level==="low").length},
  ];
  const maxVal = Math.max(...data.map(d=>d.value), 1);
  return (
    <div>
      {data.every(d=>d.value===0) ? (
        <div style={{textAlign:"center",color:C.muted,fontSize:12,padding:"20px 0"}}>
          No contract values set yet
        </div>
      ) : data.map(d=>(
        <div key={d.label} style={{marginBottom:14}}>
          <div style={{display:"flex",justifyContent:"space-between",
            fontSize:12,marginBottom:5,alignItems:"center"}}>
            <div style={{display:"flex",alignItems:"center",gap:6}}>
              <div style={{width:9,height:9,borderRadius:2,background:d.color}}/>
              <span style={{color:C.body,fontWeight:500}}>{d.label}</span>
              <span style={{color:C.muted,fontSize:10}}>({d.count})</span>
            </div>
            <span style={{fontWeight:700,color:d.color}}>{fmtValue(d.value)}</span>
          </div>
          <div style={{height:28,background:"#F1F5F9",borderRadius:6,overflow:"hidden"}}>
            <div style={{height:"100%",
              width:`${maxVal>0?(d.value/maxVal)*100:0}%`,
              background:`linear-gradient(90deg,${d.color}BB,${d.color})`,
              borderRadius:6,transition:"width 0.8s ease",
              display:"flex",alignItems:"center",paddingLeft:8}}>
              {d.value>0&&(d.value/maxVal)>0.2&&(
                <span style={{fontSize:11,fontWeight:700,color:"white"}}>{fmtValue(d.value)}</span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Chart B: Upload Activity ──────────────────────────────────────
function ActivityTimeline({ contracts }: { contracts: any[] }) {
  const now = new Date();
  const weeks = Array.from({length:8},(_,i)=>{
    const s=new Date(now); s.setDate(now.getDate()-(7-i)*7-7);
    const e=new Date(now); e.setDate(now.getDate()-(7-i)*7);
    const wc=contracts.filter(c=>{
      const d=new Date(c.created_at||c.upload_date||"");
      return d>=s&&d<e;
    });
    return {label:i===7?"Now":i===6?"1w":`${8-i}w`,count:wc.length,high:wc.filter(c=>c.risk_level==="high").length};
  });
  const maxC=Math.max(...weeks.map(w=>w.count),1);
  const chartH=80;
  return (
    <div>
      <div style={{display:"flex",alignItems:"flex-end",gap:6,height:chartH,marginBottom:6}}>
        {weeks.map((w,i)=>{
          const bH=Math.max((w.count/maxC)*chartH,w.count>0?6:0);
          const hH=w.count>0?(w.high/w.count)*bH:0;
          return (
            <div key={i} title={`${w.label}: ${w.count} (${w.high} high risk)`}
              style={{flex:1,display:"flex",flexDirection:"column",
                alignItems:"center",height:chartH,justifyContent:"flex-end"}}>
              <div style={{width:"100%",height:bH,borderRadius:"4px 4px 0 0",
                background:"#BFDBFE",position:"relative",overflow:"hidden"}}>
                {hH>0&&<div style={{position:"absolute",bottom:0,width:"100%",
                  height:hH,background:C.error}}/>}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{display:"flex",gap:6}}>
        {weeks.map((w,i)=>(
          <div key={i} style={{flex:1,textAlign:"center",fontSize:9,color:C.muted}}>{w.label}</div>
        ))}
      </div>
      <div style={{display:"flex",gap:12,marginTop:8}}>
        {[{color:"#BFDBFE",label:"All"},{color:C.error,label:"High risk"}].map(l=>(
          <div key={l.label} style={{display:"flex",alignItems:"center",gap:4}}>
            <div style={{width:10,height:10,borderRadius:2,background:l.color}}/>
            <span style={{fontSize:10,color:C.muted}}>{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Chart C: Clause Heatmap ───────────────────────────────────────
function ClauseHeatmap({ contracts }: { contracts: any[] }) {
  const map: Record<string,{total:number;high:number;medium:number}> = {};
  contracts.forEach((c:any)=>{
    (c.clauses||[]).forEach((cl:any)=>{
      const t=cl.clause_type||"other";
      if(!map[t]) map[t]={total:0,high:0,medium:0};
      map[t].total++;
      if(cl.risk_level==="high") map[t].high++;
      if(cl.risk_level==="medium") map[t].medium++;
    });
  });
  const sorted=Object.entries(map).sort((a,b)=>b[1].total-a[1].total).slice(0,10);
  if(!sorted.length) return (
    <div style={{textAlign:"center",color:C.muted,fontSize:12,padding:"20px 0"}}>
      Upload contracts to see clause distribution
    </div>
  );
  const maxT=Math.max(...sorted.map(([,v])=>v.total));
  return (
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6}}>
      {sorted.map(([type,data])=>{
        const pct=data.total/maxT;
        const rc=data.high>0?C.error:data.medium>0?C.warning:C.success;
        const label=type.replace(/_/g," ").split(" ").map((w:string)=>w.charAt(0).toUpperCase()+w.slice(1)).join(" ");
        return (
          <div key={type} style={{
            background:`${rc}${Math.round(Math.max(0.12,pct)*38).toString(16).padStart(2,"0")}`,
            border:`1px solid ${rc}${Math.round(Math.max(0.12,pct)*70).toString(16).padStart(2,"0")}`,
            borderRadius:8,padding:"8px 10px",position:"relative",overflow:"hidden"}}>
            <div style={{fontSize:10,fontWeight:700,color:C.heading,marginBottom:2,
              overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{label}</div>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <span style={{fontSize:13,fontWeight:900,color:rc}}>{data.total}</span>
              {data.high>0&&<span style={{fontSize:9,color:C.error,fontWeight:700}}>{data.high} high</span>}
            </div>
            <div style={{position:"absolute",bottom:0,left:0,right:0,height:2,
              background:rc,opacity:Math.max(0.2,pct)}}/>
          </div>
        );
      })}
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────
export default function DashboardPage() {
  const [allContracts, setAllContracts] = useState<Contract[]>([]);
  const [recentContracts, setRecent]    = useState<Contract[]>([]);
  const [obligations, setObligations]   = useState<any[]>([]);
  const [reviews, setReviews]           = useState<any[]>([]);
  const [usage, setUsage]               = useState<any>(null);
  const [insights, setInsights]         = useState<{text:string;link:string;label:string}[]>([]);
  const [loading, setLoading]           = useState(true);
  const [user, setUser]                 = useState<any>(null);
  const [summary, setSummary]           = useState<any>(null);
  const [activeRisk, setActiveRisk]     = useState<string|null>(null);

  useEffect(()=>{
    const token=getToken();
    const h={Authorization:`Bearer ${token}`};
    const load=async()=>{
      try {
        const [meRes,summaryData,contractsData,usageData,obligationsData,reviewsData]=await Promise.all([
          fetch(`${API}/api/v1/auth/me`,{headers:h}).then(r=>r.json()),
          fetch(`${API}/api/v1/billing/summary`,{headers:h}).then(r=>r.ok?r.json():null).catch(()=>null),
          contractsAPI.list({page:1,page_size:100}),
          billingAPI.usage(),
          fetch(`${API}/api/v1/obligations/?page_size=50`,{headers:h}).then(r=>r.json()),
          fetch(`${API}/api/v1/reviews/`,{headers:h}).then(r=>r.json()),
        ]);
        setUser(meRes);
        setSummary(summaryData);
        const allC=contractsData.contracts||[];
        setAllContracts(allC);
        setRecent(allC.slice(0,5));
        const rawUsage = usageData.usage || {};
        setUsage({
          queries_used:    rawUsage.queries?.used      || 0,
          queries_limit:   rawUsage.queries?.limit     || 100,
          contracts_used:  rawUsage.contracts?.used    || 0,
          contracts_limit: rawUsage.contracts?.limit   || 5,
          storage_used:    rawUsage.storage_mb?.used   || 0,
          storage_limit:   rawUsage.storage_mb?.limit  || 100,
        });
        setObligations(obligationsData.obligations||[]);
        setReviews(reviewsData.reviews||[]);
        // Insights
        const ins:{text:string;link:string;label:string}[]=[];
        const high=allC.filter((c:any)=>c.risk_level==="high").length;
        if(high>0) ins.push({text:`${high} high-risk contract${high>1?"s":""} require immediate attention`,link:"/dashboard/contracts?risk=high",label:"Review Now"});
        const overdueObs=(obligationsData.obligations||[]).filter((o:any)=>o.due_date&&o.status!=="completed"&&new Date(o.due_date)<new Date());
        if(overdueObs.length>0) ins.push({text:`${overdueObs.length} overdue obligation${overdueObs.length>1?"s":""} need attention`,link:"/dashboard/obligations",label:"Resolve"});
        const expiring=allC.filter((c:any)=>{if(!c.expiry_date)return false;const d=Math.ceil((new Date(c.expiry_date).getTime()-Date.now())/86400000);return d>0&&d<=30;});
        if(expiring.length>0) ins.push({text:`${expiring.length} contract${expiring.length>1?"s":""} expiring within 30 days`,link:"/dashboard/contracts",label:"View"});
        const pending=(reviewsData.reviews||[]).filter((r:any)=>r.status==="pending"||r.status==="in_review");
        if(pending.length>0) ins.push({text:`${pending.length} contract${pending.length>1?"s":""} awaiting legal review`,link:"/dashboard/reviews",label:"Review"});
        setInsights(ins);
      } catch(e){console.error(e);}
      finally{setLoading(false);}
    };
    load();
  },[]);

  const stats=useMemo(()=>({
    total:  allContracts.length,
    high:   allContracts.filter(c=>c.risk_level==="high").length,
    medium: allContracts.filter(c=>c.risk_level==="medium").length,
    low:    allContracts.filter(c=>c.risk_level==="low").length,
    pending:reviews.filter((r:any)=>r.status==="pending"||r.status==="in_review").length,
    due:    obligations.filter((o:any)=>o.due_date&&o.status!=="completed"&&
              Math.ceil((new Date(o.due_date).getTime()-Date.now())/86400000)<=30&&
              new Date(o.due_date)>new Date()).length,
  }),[allContracts,reviews,obligations]);

  const counterpartyRisk=useMemo(()=>{
    const src=activeRisk?allContracts.filter(c=>c.risk_level===activeRisk):allContracts;
    const map:Record<string,{high:number,medium:number,low:number,total:number}>={};
    src.forEach(c=>{const cp=c.counterparty||"Unknown";if(!map[cp])map[cp]={high:0,medium:0,low:0,total:0};map[cp].total++;if(c.risk_level)map[cp][c.risk_level as "high"|"medium"|"low"]++;});
    return Object.entries(map).sort((a,b)=>b[1].high-a[1].high||b[1].total-a[1].total).slice(0,5);
  },[allContracts,activeRisk]);

  const reviewPipeline=useMemo(()=>{
    const m:Record<string,number>={};
    reviews.forEach((r:any)=>{m[r.status]=(m[r.status]||0)+1;});
    return m;
  },[reviews]);

  const dueObligations=useMemo(()=>
    obligations.filter(o=>o.due_date&&o.status!=="completed")
      .sort((a,b)=>new Date(a.due_date).getTime()-new Date(b.due_date).getTime())
      .slice(0,4)
  ,[obligations]);

  const usagePct=(key:string,lim:number)=>{const u=usage?.[key]||0;return lim>0?Math.round((u/lim)*100):0;};

  if(loading) return (
    <div style={{height:"50vh",display:"flex",alignItems:"center",justifyContent:"center"}}>
      <div style={{width:32,height:32,borderRadius:"50%",border:`2px solid ${C.primary}`,
        borderTopColor:"transparent",animation:"spin 0.8s linear infinite"}}/>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  const kpis = [
    {Icon:FileText,     label:"Total Contracts", value:stats.total,           sub:`${allContracts.filter(c=>c.status==="analyzed").length} analyzed · of ${(usage?.contracts_limit||100).toLocaleString()} limit`,  color:C.primary, bg:C.primaryLight, usageKey:"contracts_used", limit:usage?.contracts_limit||100},
    {Icon:AlertTriangle,label:"High Risk",        value:stats.high,            sub:"Requires action",   color:C.error,   bg:"#FEF2F2",    usageKey:null, limit:0},
    {Icon:ClipboardList,label:"Pending Reviews",  value:stats.pending,         sub:"Awaiting decision", color:"#9333EA", bg:"#FAF5FF",    usageKey:null, limit:0},
    {Icon:Clock,        label:"Due Obligations",  value:stats.due,             sub:"Within 30 days",    color:C.warning, bg:"#FFFBEB",    usageKey:null, limit:0},
    {Icon:Zap,          label:"AI Queries",       value:usage?.queries_used||0,sub:`of ${(usage?.queries_limit||100).toLocaleString()}`, color:"#8B5CF6", bg:"#F5F3FF", usageKey:"queries_used", limit:usage?.queries_limit||100},
  ];

  return (
    <div style={{padding:"28px 32px",maxWidth:1100,margin:"0 auto"}}>

      {/* Header */}
      <div style={{marginBottom:20}}>
        <h1 style={{fontSize:22,fontWeight:800,color:C.heading,marginBottom:2}}>
          {getGreeting()}{user?.full_name?`, ${user.full_name.split(" ")[0]}`:""}
        </h1>
        <p style={{fontSize:13,color:C.muted}}>Here's what needs your attention today</p>
      </div>


      {/* Expiry / Grace Period Banner */}
      {(()=>{
        if (!summary) return null;
        const status   = (summary as any).payment_status;
        const nextDate = (summary as any).next_billing_date;
        const graceEnd = (summary as any).grace_period_end;

        if (status === "grace_period" && graceEnd) {
          const daysLeft = Math.ceil((new Date(graceEnd).getTime()-Date.now())/86400000);
          return (
            <div style={{background:"#FEF2F2",border:"1px solid #FECACA",
              borderRadius:12,padding:"14px 20px",marginBottom:16,
              display:"flex",alignItems:"center",justifyContent:"space-between",gap:12}}>
              <div>
                <div style={{fontSize:13,fontWeight:700,color:"#DC2626",marginBottom:3}}>
                  ⚠️ Payment overdue — {daysLeft} day{daysLeft!==1?"s":""} left before downgrade
                </div>
                <div style={{fontSize:11,color:"#EF4444"}}>
                  Your account will be downgraded to Free on {new Date(graceEnd).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}. Renew now to keep full access.
                </div>
              </div>
              <Link href="/dashboard/admin/billing"
                style={{padding:"8px 16px",background:"#DC2626",color:"white",
                  borderRadius:8,fontSize:12,fontWeight:700,
                  textDecoration:"none",whiteSpace:"nowrap",flexShrink:0}}>
                Renew Now →
              </Link>
            </div>
          );
        }

        if (status === "expired") {
          return (
            <div style={{background:"#1F2937",borderRadius:12,padding:"14px 20px",
              marginBottom:16,display:"flex",alignItems:"center",
              justifyContent:"space-between",gap:12}}>
              <div>
                <div style={{fontSize:13,fontWeight:700,color:"white",marginBottom:3}}>
                  Your plan has expired — you are now on the Free plan
                </div>
                <div style={{fontSize:11,color:"#9CA3AF"}}>
                  Your data is preserved. Upgrade anytime to restore full access.
                </div>
              </div>
              <Link href="/dashboard/admin/billing"
                style={{padding:"8px 16px",background:"#0066FF",color:"white",
                  borderRadius:8,fontSize:12,fontWeight:700,
                  textDecoration:"none",whiteSpace:"nowrap",flexShrink:0}}>
                Upgrade →
              </Link>
            </div>
          );
        }

        if (nextDate && (summary?.plan || user?.plan || "free") !== "free") {
          const daysLeft = Math.ceil((new Date(nextDate).getTime()-Date.now())/86400000);
          if (daysLeft <= 15) {
            return (
              <div style={{background:"#FFFBEB",border:"1px solid #FDE68A",
                borderRadius:12,padding:"14px 20px",marginBottom:16,
                display:"flex",alignItems:"center",justifyContent:"space-between",gap:12}}>
                <div>
                  <div style={{fontSize:13,fontWeight:700,color:"#92400E",marginBottom:3}}>
                    📅 Your {summary?.plan || user?.plan || ""} plan expires in {daysLeft} day{daysLeft!==1?"s":""}
                  </div>
                  <div style={{fontSize:11,color:"#B45309"}}>
                    Renews on {new Date(nextDate).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}. Renew early to avoid interruption.
                  </div>
                </div>
                <a href="/dashboard/admin/billing"
                  style={{padding:"8px 16px",background:"#F59E0B",color:"white",
                    borderRadius:8,fontSize:12,fontWeight:700,
                    textDecoration:"none",whiteSpace:"nowrap",flexShrink:0}}>
                  Renew →
                </a>
              </div>
            );
          }
        }
        return null;
      })()}


      {/* Upgrade Banner — free/starter only */}
      {(()=>{
        const plan = summary?.plan || user?.plan || "free";
        if (plan === "free") return (
          <div style={{background:"linear-gradient(135deg,#0A1128,#0066FF)",
            borderRadius:12,padding:"14px 20px",marginBottom:20,
            display:"flex",alignItems:"center",justifyContent:"space-between",gap:12}}>
            <div>
              <div style={{fontSize:13,fontWeight:700,color:"white",marginBottom:3}}>
                🚀 Upgrade to Starter — unlock AI Copilot, reviews & more
              </div>
              <div style={{fontSize:11,color:"rgba(255,255,255,0.7)"}}>
                Starting at ₹3,999/mo · 5 contracts free to try
              </div>
            </div>
            <Link href="/dashboard/admin/billing"
              style={{padding:"8px 18px",background:"white",borderRadius:8,
                fontSize:12,fontWeight:700,textDecoration:"none",
                color:"#0066FF",flexShrink:0,whiteSpace:"nowrap"}}>
              Upgrade Now →
            </Link>
          </div>
        );
        if (plan === "starter") return (
          <div style={{background:"linear-gradient(135deg,#0A1128,#7C3AED)",
            borderRadius:12,padding:"14px 20px",marginBottom:20,
            display:"flex",alignItems:"center",justifyContent:"space-between",gap:12}}>
            <div>
              <div style={{fontSize:13,fontWeight:700,color:"white",marginBottom:3}}>
                ⚡ Upgrade to Professional — unlimited contracts & advanced AI
              </div>
              <div style={{fontSize:11,color:"rgba(255,255,255,0.7)"}}>
                ₹16,499/mo · Industry scoring, bulk import & priority support
              </div>
            </div>
            <Link href="/dashboard/admin/billing"
              style={{padding:"8px 18px",background:"white",borderRadius:8,
                fontSize:12,fontWeight:700,textDecoration:"none",
                color:"#7C3AED",flexShrink:0,whiteSpace:"nowrap"}}>
              Upgrade Now →
            </Link>
          </div>
        );
        return null;
      })()}

      {/* AI Insights Banner */}
      {insights.length>0&&(
        <div style={{background:C.navy,borderRadius:12,padding:"16px 20px",marginBottom:20}}>
          <div style={{fontSize:11,fontWeight:700,color:"#94A3B8",textTransform:"uppercase",
            letterSpacing:"0.06em",marginBottom:10}}>✦ AI Insights</div>
          <div style={{display:"flex",flexDirection:"column",gap:8}}>
            {insights.map((ins,i)=>(
              <div key={i} style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:12}}>
                <span style={{fontSize:13,color:"rgba(255,255,255,0.85)",flex:1}}>• {ins.text}</span>
                <Link href={ins.link} style={{fontSize:11,fontWeight:700,color:C.primary,
                  background:C.primaryLight,padding:"4px 10px",borderRadius:20,
                  textDecoration:"none",whiteSpace:"nowrap",
                  display:"flex",alignItems:"center",gap:4,flexShrink:0}}>
                  {ins.label} <ArrowRight size={10}/>
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KPI strip */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:12,marginBottom:20}}>
        {kpis.map(kpi=>(
          <div key={kpi.label} style={{background:C.surface,border:`1px solid ${C.border}`,
            borderRadius:12,padding:"16px 18px",boxShadow:"0 1px 3px rgba(0,0,0,0.04)"}}>
            <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8}}>
              <div style={{width:28,height:28,borderRadius:7,background:kpi.bg,
                display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                <kpi.Icon size={13} style={{color:kpi.color}}/>
              </div>
              <span style={{fontSize:11,color:C.muted,fontWeight:500}}>{kpi.label}</span>
            </div>
            <div style={{fontSize:26,fontWeight:900,color:C.heading,lineHeight:1,marginBottom:2}}>
              {kpi.value.toLocaleString()}
            </div>
            <div style={{fontSize:10,color:C.muted}}>{kpi.sub}</div>
            {kpi.usageKey&&kpi.limit>0&&(
              <ProgressBar pct={usagePct(kpi.usageKey,kpi.limit)}
                color={usagePct(kpi.usageKey,kpi.limit)>80?C.error:kpi.color}/>
            )}
          </div>
        ))}
      </div>

      {/* Charts row 1 */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:16}}>

        {/* Donut + counterparty */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{padding:"14px 18px",borderBottom:`1px solid ${C.border}`,
            display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span style={{fontSize:13,fontWeight:700,color:C.heading}}>Risk Distribution</span>
            <Link href="/dashboard/contracts" style={{fontSize:11,color:C.primary,
              textDecoration:"none",fontWeight:600,display:"flex",alignItems:"center",gap:3}}>
              View all <ChevronRight size={11}/>
            </Link>
          </div>
          <div style={{padding:"16px 18px"}}>
            <div style={{display:"flex",alignItems:"center",gap:20,marginBottom:16}}>
              <DonutChart high={stats.high} medium={stats.medium} low={stats.low}
                total={stats.total} activeLevel={activeRisk} onHover={setActiveRisk}/>
              <div style={{flex:1}}>
                {[{key:"high",label:"High Risk",count:stats.high,color:C.error},
                  {key:"medium",label:"Medium Risk",count:stats.medium,color:C.warning},
                  {key:"low",label:"Low Risk",count:stats.low,color:C.success}]
                  .map(seg=>{
                    const pct=stats.total>0?Math.round(seg.count/stats.total*100):0;
                    const isActive=activeRisk===seg.key;
                    return (
                      <div key={seg.key}
                        onMouseEnter={()=>setActiveRisk(seg.key)}
                        onMouseLeave={()=>setActiveRisk(null)}
                        style={{display:"flex",alignItems:"center",gap:8,marginBottom:8,
                          cursor:"pointer",opacity:activeRisk&&!isActive?0.4:1,transition:"opacity 0.2s"}}>
                        <div style={{width:10,height:10,borderRadius:2,background:seg.color,flexShrink:0}}/>
                        <span style={{fontSize:12,color:C.body,flex:1}}>{seg.label}</span>
                        <span style={{fontSize:12,fontWeight:700,color:seg.color}}>{seg.count}</span>
                        <span style={{fontSize:11,color:C.muted,width:34,textAlign:"right"}}>{pct}%</span>
                      </div>
                    );
                  })}
              </div>
            </div>
            {counterpartyRisk.length>0&&(
              <>
                <div style={{fontSize:11,fontWeight:700,color:C.muted,textTransform:"uppercase",
                  letterSpacing:"0.05em",marginBottom:8}}>
                  {activeRisk?`${activeRisk} risk counterparties`:"Counterparty Activity"}
                </div>
                {counterpartyRisk.map(([cp,risk])=>(
                  <div key={cp} style={{display:"flex",alignItems:"center",
                    justifyContent:"space-between",padding:"5px 0",
                    borderBottom:`1px solid ${C.border}`}}>
                    <span style={{fontSize:12,color:C.body,flex:1,overflow:"hidden",
                      textOverflow:"ellipsis",whiteSpace:"nowrap",marginRight:8}}>{cp}</span>
                    <div style={{display:"flex",gap:4,flexShrink:0}}>
                      {risk.high>0&&<span style={{fontSize:10,fontWeight:700,padding:"2px 7px",
                        borderRadius:20,background:"#FEF2F2",color:C.error}}>{risk.high} High</span>}
                      {risk.medium>0&&<span style={{fontSize:10,fontWeight:600,padding:"2px 7px",
                        borderRadius:20,background:"#FFFBEB",color:C.warning}}>{risk.medium} Med</span>}
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        {/* Pipeline funnel */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{padding:"14px 18px",borderBottom:`1px solid ${C.border}`,
            display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <div>
              <span style={{fontSize:13,fontWeight:700,color:C.heading}}>Review Pipeline</span>
              {reviews.length>0&&<span style={{fontSize:11,color:C.muted,marginLeft:8}}>
                {reviews.length} total</span>}
            </div>
            <Link href="/dashboard/reviews" style={{fontSize:11,color:C.primary,
              textDecoration:"none",fontWeight:600,display:"flex",alignItems:"center",gap:3}}>
              View all <ChevronRight size={11}/>
            </Link>
          </div>
          <div style={{padding:"16px 18px"}}>
            <PipelineFunnel pipeline={reviewPipeline} total={reviews.length}/>
            {reviews.length>0&&(
              <div style={{marginTop:14}}>
                <div style={{fontSize:11,fontWeight:700,color:C.muted,textTransform:"uppercase",
                  letterSpacing:"0.05em",marginBottom:8}}>Stage Breakdown</div>
                {[{status:"in_review",label:"In Review",Icon:Eye,color:C.warning},
                  {status:"pending",label:"Pending",Icon:Clock,color:"#9333EA"},
                  {status:"approved",label:"Approved",Icon:CheckCircle,color:C.success},
                  {status:"rejected",label:"Rejected",Icon:XCircle,color:C.error},
                  {status:"revision_requested",label:"Revision",Icon:RotateCcw,color:"#F97316"}]
                  .filter(s=>reviewPipeline[s.status]>0).map(stage=>{
                    const rc=reviews.filter((r:any)=>r.status===stage.status);
                    return (
                      <div key={stage.status} style={{marginBottom:8}}>
                        <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:2}}>
                          <stage.Icon size={11} style={{color:stage.color,flexShrink:0}}/>
                          <span style={{fontSize:11,fontWeight:600,color:stage.color}}>{stage.label}</span>
                          <span style={{fontSize:11,color:C.muted}}>({reviewPipeline[stage.status]})</span>
                        </div>
                        <div style={{paddingLeft:17,fontSize:11,color:C.muted,
                          overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                          {rc.slice(0,2).map((r:any)=>r.contract_title||r.id?.slice(0,8)).join(", ")}
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Obligations + Recent */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:16}}>
        {/* Obligations */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{padding:"14px 18px",borderBottom:`1px solid ${C.border}`,
            display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span style={{fontSize:13,fontWeight:700,color:C.heading}}>Obligations Due</span>
            <Link href="/dashboard/obligations" style={{fontSize:11,color:C.primary,
              textDecoration:"none",fontWeight:600,display:"flex",alignItems:"center",gap:3}}>
              View all <ChevronRight size={11}/>
            </Link>
          </div>
          <div style={{padding:"12px 14px"}}>
            <ObligationTimeline obligations={dueObligations}/>
            {dueObligations.length===0?(
              <div style={{textAlign:"center",padding:"24px 0",color:C.muted,fontSize:12}}>
                No upcoming obligations
              </div>
            ):dueObligations.map((o:any,i:number)=>{
              const days=Math.ceil((new Date(o.due_date).getTime()-Date.now())/86400000);
              const overdue=days<0; const urgent=days>=0&&days<=7;
              return (
                <div key={o.id||i} style={{
                  background:overdue?"#FEF2F2":urgent?"#FFFBEB":C.bg,
                  border:`1px solid ${overdue?C.error:urgent?C.warning:C.border}`,
                  borderRadius:10,padding:"10px 14px",marginBottom:8,
                  display:"flex",alignItems:"center",justifyContent:"space-between",gap:10}}>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontSize:12,fontWeight:700,color:C.heading,marginBottom:2,
                      overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                      {o.title||o.obligation_type||"Obligation"}
                    </div>
                    <div style={{fontSize:10,color:C.muted}}>
                      {o.contract_title||""}{o.amount?` • ${o.currency||""}${Number(o.amount).toLocaleString()}`:""}
                    </div>
                  </div>
                  <span style={{fontSize:10,fontWeight:700,padding:"3px 9px",borderRadius:20,
                    background:overdue?"#FEE2E2":urgent?"#FEF3C7":"#F1F5F9",
                    color:overdue?C.error:urgent?C.warning:C.muted,
                    whiteSpace:"nowrap",flexShrink:0}}>
                    {overdue?`${Math.abs(days)}d Overdue`:days===0?"Due Today":`Due in ${days}d`}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent contracts */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{padding:"14px 18px",borderBottom:`1px solid ${C.border}`,
            display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span style={{fontSize:13,fontWeight:700,color:C.heading}}>Recent Contracts</span>
            <Link href="/dashboard/contracts" style={{fontSize:11,color:C.primary,
              textDecoration:"none",fontWeight:600,display:"flex",alignItems:"center",gap:3}}>
              View all <ChevronRight size={11}/>
            </Link>
          </div>
          <div style={{padding:"6px 0"}}>
            {recentContracts.length===0?(
              <div style={{textAlign:"center",padding:"24px 0",color:C.muted,fontSize:12}}>
                No contracts yet
              </div>
            ):recentContracts.map((c:any)=>(
              <Link key={c.id} href={`/dashboard/contracts/${c.id}`}
                style={{display:"flex",alignItems:"center",gap:10,padding:"10px 18px",
                  textDecoration:"none",borderBottom:`1px solid ${C.border}`,transition:"background 0.1s"}}
                onMouseEnter={e=>(e.currentTarget as HTMLElement).style.background=C.bg}
                onMouseLeave={e=>(e.currentTarget as HTMLElement).style.background="transparent"}>
                <div style={{width:7,height:7,borderRadius:"50%",flexShrink:0,
                  background:c.risk_level==="high"?C.error:c.risk_level==="medium"?C.warning:C.success}}/>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontSize:12,fontWeight:600,color:C.heading,
                    overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{c.title}</div>
                  <div style={{fontSize:10,color:C.muted,marginTop:1}}>
                    {c.counterparty||""}{c.contract_value?` • ₹${(c.contract_value/100000).toFixed(1)}L`:""}
                  </div>
                </div>
                <StatusBadge status={c.status||"analyzed"}/>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Charts row 2 — A, B, C */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:16}}>

        {/* A: Value by Risk */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{padding:"14px 18px",borderBottom:`1px solid ${C.border}`}}>
            <div style={{fontSize:13,fontWeight:700,color:C.heading}}>Contract Value by Risk</div>
            <div style={{fontSize:11,color:C.muted}}>Financial exposure breakdown</div>
          </div>
          <div style={{padding:"16px 18px"}}>
            <ValueByRiskChart contracts={allContracts}/>
          </div>
        </div>

        {/* B: Activity */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{padding:"14px 18px",borderBottom:`1px solid ${C.border}`}}>
            <div style={{fontSize:13,fontWeight:700,color:C.heading}}>Upload Activity</div>
            <div style={{fontSize:11,color:C.muted}}>Last 8 weeks</div>
          </div>
          <div style={{padding:"16px 18px"}}>
            <ActivityTimeline contracts={allContracts}/>
          </div>
        </div>

        {/* C: Clause Heatmap */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{padding:"14px 18px",borderBottom:`1px solid ${C.border}`}}>
            <div style={{fontSize:13,fontWeight:700,color:C.heading}}>Clause Distribution</div>
            <div style={{fontSize:11,color:C.muted}}>Most frequent clause types</div>
          </div>
          <div style={{padding:"16px 18px"}}>
            <ClauseHeatmap contracts={allContracts}/>
          </div>
        </div>
      </div>

    </div>
  );
}
