"use client";
import { ClauStorLoader } from "@/components/shared/ClauStorLoader";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { ProfilePopup } from "@/components/layout/ProfilePopup";
import { UploadModal } from "@/components/layout/UploadModal";
import { CommandPalette } from "@/components/layout/CommandPalette";
import {
  LayoutDashboard, FileText, Sparkles, CheckSquare,
  GitCompare, BookOpen, Clock, BarChart2, UploadCloud,
  Users, ShieldCheck, CreditCard, History, Settings,
  ChevronLeft, ChevronRight, LogOut, Bell
} from "lucide-react";

const C = {
  primary: "#5B4BFF", primaryLight: "#EEF0FF",
  heading: "#111827", body: "#374151", muted: "#6B7280",
  border: "#E5E7EB", surface: "#FFFFFF", bg: "#FAFBFC",
  sidebar: "#1C1B2E", sidebarText: "rgba(255,255,255,0.7)",
  sidebarActive: "rgba(91,75,255,0.25)",
};

// Permission → nav item mapping
// Features locked per plan with upgrade messaging
const LOCKED_FEATURES: Record<string,{plan:string;label:string;benefits:string[]}> = {
  "bulk:import":     {plan:"starter",  label:"Bulk Import",
    benefits:["Import 100+ contracts at once","Auto-process entire folders","Excel & XML batch support"]},
  "playbook:view":   {plan:"starter",  label:"Playbook",
    benefits:["Compare clauses vs standard templates","See % match per clause","Flag deviations automatically"]},
  "obligations:view":{plan:"starter",  label:"Obligations",
    benefits:["Track payment & delivery deadlines","Email alerts before due dates","Calendar integration"]},
  "reviews:view":    {plan:"starter",  label:"Review Workflow",
    benefits:["Assign contracts to legal reviewers","Clause-by-clause approval","SLA tracking"]},
  "users:view":      {plan:"starter",  label:"Team Management",
    benefits:["Invite team members","Role-based access control","Activity tracking per user"]},
  "billing:view":    {plan:"free",     label:"Billing",
    benefits:["Manage subscription","Add industry packs","Download invoices"]},
  "audit:view":      {plan:"professional", label:"Audit Log",
    benefits:["Full access trail — who viewed what","Export audit CSV","GDPR compliance proof"]},
  "settings:manage": {plan:"starter",  label:"Settings",
    benefits:["Custom org settings","API keys","Notification preferences"]},
};

// Professional advantages shown in upgrade modal
const PRO_ADVANTAGES = [
  {icon:"⚡", title:"10× Faster Processing",    desc:"Dedicated processing queue — no shared workers"},
  {icon:"🤖", title:"25 Clause Types",           desc:"vs 10 on free — includes escrow, benchmarking, audit rights"},
  {icon:"📋", title:"Playbook Similarity",       desc:"Compare every clause against your standard templates"},
  {icon:"🛡️", title:"PII Masking",               desc:"Presidio AI masks names, emails, phone numbers automatically"},
  {icon:"🔗", title:"Clause Relationships",      desc:"Auto-maps payment→termination→SLA cross-references"},
  {icon:"📊", title:"Industry Risk Weights",     desc:"Healthcare 2×, Tech IP 2× — industry-calibrated scoring"},
  {icon:"📦", title:"Data Export (GDPR Art.20)", desc:"Download all your data as ZIP anytime"},
  {icon:"📋", title:"Full Audit Trail",          desc:"Every access logged — SOC2 and compliance ready"},
];

const NAV_ITEMS = [
  { href:"/dashboard",             Icon:LayoutDashboard, label:"Overview",      permission: null },
  { href:"/dashboard/contracts",   Icon:FileText,        label:"Contracts",     permission:"contracts:view" },
  { href:"/dashboard/copilot",     Icon:Sparkles,        label:"AI Copilot",    permission:"chat:use" },
  { href:"/dashboard/reviews",     Icon:CheckSquare,     label:"Reviews",       permission:"reviews:view" },
  { href:"/dashboard/compare",     Icon:GitCompare,      label:"Compare",       permission:"contracts:view" },
  { href:"/dashboard/playbook",    Icon:BookOpen,        label:"Playbook",      permission:"playbook:view" },
  { href:"/dashboard/obligations", Icon:Clock,           label:"Obligations",   permission:"obligations:view" },
  { href:"/dashboard/analytics",   Icon:BarChart2,       label:"Analytics",     permission:"analytics:view" },
  { href:"/dashboard/bulk",        Icon:UploadCloud,     label:"Bulk Import",   permission:"bulk:import" },
];

const ADMIN_NAV = [
  { href:"/dashboard/admin/users",  Icon:Users,       label:"Users",     permission:"users:view" },
  { href:"/dashboard/admin/roles",  Icon:ShieldCheck, label:"Roles",     permission:"users:manage" },
  { href:"/dashboard/admin/billing",Icon:CreditCard,  label:"Billing",   permission:"billing:view" },
  { href:"/dashboard/admin/observability", Icon:BarChart2, label:"AI Insights", permission:"ai_insights:view" },
  { href:"/dashboard/admin/audit",  Icon:History,     label:"Audit Log", permission:"audit:view" },
  { href:"/dashboard/settings",     Icon:Settings,    label:"Settings",  permission:"settings:manage" },
];

// Role → permissions map (mirrors backend)
const ROLE_PERMISSIONS: Record<string, string[]> = {
  super_admin:      ["*"],
  dept_admin:       ["contracts:view","contracts:upload","contracts:delete","contracts:reprocess","chat:use","reviews:assign","reviews:view","analytics:view","analytics:export","users:view","users:invite","obligations:view","obligations:complete","playbook:view","playbook:manage","bulk:import","settings:manage","billing:view"],
  contract_manager: ["contracts:view","contracts:upload","contracts:delete","contracts:reprocess","chat:use","reviews:assign","reviews:view","analytics:view","obligations:view","obligations:complete","playbook:view","bulk:import"],
  legal_reviewer:   ["contracts:view","chat:use","reviews:view","reviews:decide","analytics:view","obligations:view","playbook:view"],
  business_viewer:  ["contracts:view","chat:use","analytics:view","obligations:view"],
};

// Plan → features unlocked
const PLAN_FEATURES: Record<string, string[]> = {
  free:         ["contracts:view","contracts:upload","chat:use","analytics:view","billing:view"],
  starter:      ["contracts:view","contracts:upload","contracts:delete","chat:use","reviews:view","reviews:assign","analytics:view","analytics:export","obligations:view","obligations:complete","bulk:import","playbook:view","billing:view","settings:manage","users:view"],
  professional: ["*"],
  enterprise:   ["*"],
};

function hasPermission(role: string, permission: string | null, plan = "free"): boolean {
  if (!permission) return true;
  // Check role permission
  const rolePerms = ROLE_PERMISSIONS[role] || [];
  const hasRole = rolePerms.includes("*") || rolePerms.includes(permission);
  // Check plan feature
  const planFeatures = PLAN_FEATURES[plan] || PLAN_FEATURES["free"];
  const hasPlan = planFeatures.includes("*") || planFeatures.includes(permission);
  return hasRole && hasPlan;
}


// ── Upgrade Modal ─────────────────────────────────────────────────────────────
function UpgradeModal({feature, plan, onClose}: {
  feature:string; plan:string; onClose:()=>void;
}) {
  const info = LOCKED_FEATURES[feature];
  const isPro = plan === "professional";
  const planName = isPro ? "Professional" : "Starter";
  const planPrice = isPro ? "₹16,499" : "₹3,999";
  const advantages = isPro ? PRO_ADVANTAGES : PRO_ADVANTAGES.slice(0,4);

  return (
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",
      display:"flex",alignItems:"center",justifyContent:"center",zIndex:2000}}
      onClick={onClose}>
      <div style={{background:"white",borderRadius:16,padding:0,
        width:"100%",maxWidth:520,boxShadow:"0 20px 60px rgba(0,0,0,0.2)",
        overflow:"hidden"}}
        onClick={e=>e.stopPropagation()}>

        {/* Header */}
        <div style={{background:"#0A1128",padding:"24px 28px",position:"relative"}}>
          <button onClick={onClose}
            style={{position:"absolute",top:16,right:16,background:"rgba(255,255,255,0.1)",
              border:"none",borderRadius:6,color:"white",cursor:"pointer",
              width:28,height:28,display:"flex",alignItems:"center",justifyContent:"center",
              fontSize:16}}>×</button>
          <div style={{fontSize:12,fontWeight:700,color:"#00A3FF",
            textTransform:"uppercase",letterSpacing:"0.08em",marginBottom:6}}>
            🔒 Unlock {info?.label||feature}
          </div>
          <div style={{fontSize:20,fontWeight:800,color:"white",marginBottom:4}}>
            Available on {planName} plan
          </div>
          <div style={{fontSize:14,color:"rgba(255,255,255,0.6)"}}>
            {planPrice}/mo + GST · Upgrade in seconds
          </div>
        </div>

        <div style={{padding:"20px 28px"}}>
          {/* Feature benefits */}
          {info?.benefits && (
            <div style={{marginBottom:20}}>
              <div style={{fontSize:12,fontWeight:700,color:"#64748B",
                textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:10}}>
                What you unlock
              </div>
              {info.benefits.map(b=>(
                <div key={b} style={{display:"flex",gap:8,alignItems:"center",
                  padding:"6px 0",borderBottom:"1px solid #F1F5F9",fontSize:13}}>
                  <span style={{color:"#22C55E",fontWeight:700}}>✓</span>
                  <span style={{color:"#334155"}}>{b}</span>
                </div>
              ))}
            </div>
          )}

          {/* Pro advantages */}
          {isPro && (
            <div style={{marginBottom:20}}>
              <div style={{fontSize:12,fontWeight:700,color:"#64748B",
                textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:10}}>
                Professional advantages
              </div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
                {advantages.map(a=>(
                  <div key={a.title} style={{padding:"10px 12px",borderRadius:8,
                    background:"#F8FAFC",border:"1px solid #E2E8F0"}}>
                    <div style={{fontSize:16,marginBottom:4}}>{a.icon}</div>
                    <div style={{fontSize:12,fontWeight:700,color:"#111827",marginBottom:2}}>
                      {a.title}
                    </div>
                    <div style={{fontSize:11,color:"#64748B",lineHeight:1.4}}>{a.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* CTAs */}
          <div style={{display:"flex",gap:10}}>
            <a href="/dashboard/admin/billing"
              onClick={onClose}
              style={{flex:2,padding:"12px",borderRadius:10,
                background:"#0066FF",color:"white",border:"none",
                fontSize:14,fontWeight:700,cursor:"pointer",textAlign:"center",
                textDecoration:"none",display:"block",
                boxShadow:"0 4px 12px rgba(0,102,255,0.3)"}}>
              Upgrade to {planName} →
            </a>
            <button onClick={onClose}
              style={{flex:1,padding:"12px",borderRadius:10,
                background:"transparent",color:"#64748B",
                border:"1px solid #E2E8F0",fontSize:14,cursor:"pointer"}}>
              Maybe later
            </button>
          </div>
          <p style={{fontSize:11,color:"#94A3B8",textAlign:"center",marginTop:10}}>
            No commitment · Cancel anytime · Instant activation
          </p>
        </div>
      </div>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router   = useRouter();
  const { user, token, loadUser, logout } = useAuthStore();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const init = async () => {
      // Check store token first, then localStorage fallback
      const storedAuth = typeof window !== "undefined"
        ? (() => { try { return JSON.parse(localStorage.getItem("claustor-auth")||"{}"); } catch { return {}; } })()
        : {};
      const effectiveToken = token || storedAuth?.state?.token;
      if (!effectiveToken) { router.push("/login"); return; }
      // Always reload user to get latest plan from DB
      await loadUser();
      setChecked(true);
    };
    init();
  }, []);

  useEffect(() => {
    if (checked && !user && !token) router.push("/login");
  }, [checked, user, token]);

  const [collapsed, setCollapsed] = useState(false);
  const [upgradeModal, setUpgradeModal] = useState<{feature:string;plan:string}|null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [bgJob, setBgJob] = useState<{contractId:string; fileName:string; done:boolean}|null>(null);

  // Poll background job until done
  useEffect(()=>{
    if (!bgJob || bgJob.done) return;
    const t = localStorage.getItem("claustor-auth");
    const tok = t ? (() => { try { return JSON.parse(t)?.state?.token||""; } catch { return ""; } })() : "";
    const poll = setInterval(async ()=>{
      try {
        const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/contracts/${bgJob.contractId}/status`,
          { headers: { Authorization: `Bearer ${tok}` } });
        if (!r.ok) return;
        const d = await r.json();
        if (d.status === "analyzed" || d.status === "error") {
          clearInterval(poll);
          setBgJob(prev => prev ? {...prev, done: true} : null);
        }
      } catch {}
    }, 3000);
    return () => clearInterval(poll);
  }, [bgJob?.contractId, bgJob?.done]);
  const [navBadges, setNavBadges] = useState<Record<string,number>>({});

  useEffect(()=>{
    if(!user) return;
    const token = typeof window!=="undefined"
      ? (() => { try { return JSON.parse(localStorage.getItem("claustor-auth")||"{}").token||""; } catch{ return ""; } })()
      : "";
    const h = {Authorization:`Bearer ${token}`};
    // Load pending reviews + upcoming obligations counts
    Promise.all([
      fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/reviews/my-queue",{headers:h})
        .then(r=>r.ok?r.json():{queue:[]}).catch(()=>({queue:[]})),
      fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/obligations/?status=pending&due_soon=true",{headers:h})
        .then(r=>r.ok?r.json():{obligations:[]}).catch(()=>({obligations:[]})),
    ]).then(([rev, obl])=>{
      setNavBadges({
        "/dashboard/reviews":     (rev.queue||[]).length,
        "/dashboard/obligations": (obl.obligations||[]).filter((o:any)=>o.status==="pending").length,
      });
    });
  },[user]);
  if (!checked || !user) {
    return (
      <div style={{height:"100vh",display:"flex",alignItems:"center",justifyContent:"center",background:C.bg}}>
        <div style={{textAlign:"center"}}>
          <div style={{position:"relative",width:44,height:44,margin:"0 auto 16px"}}>
            <div style={{position:"absolute",inset:0,borderRadius:"50%",border:"3px solid #EFF6FF",borderTopColor:"#0066FF",animation:"spin 1s linear infinite"}}/>
            <div style={{position:"absolute",inset:6,borderRadius:"50%",border:"2px solid #DBEAFE",borderBottomColor:"#60A5FA",animation:"spin 0.7s linear infinite reverse"}}/>
            <div style={{position:"absolute",inset:16,borderRadius:"50%",background:"#0066FF"}}/>
          </div>
          <p style={{color:C.muted,fontSize:14}}>Loading...</p>
        </div>
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    );
  }

  const isActive = (href: string) => href === "/dashboard" ? pathname === href : pathname.startsWith(href);
  const isAdmin  = ["super_admin","dept_admin","member"].includes(user.role);
  const sidebarWidth = collapsed ? 64 : 240;

  const planBadgeColor: Record<string,string> = {
    free:"#6B7280", starter:"#3B82F6", professional:"#5B4BFF", enterprise:"#F59E0B",
  };

  // Filter nav based on role permissions
  const visibleNav = NAV_ITEMS.filter(item => hasPermission(user.role, item.permission, user.plan));
  const visibleAdmin = ADMIN_NAV.filter(item => hasPermission(user.role, item.permission, user.plan));


  return (
    <div style={{display:"flex",height:"100vh",overflow:"hidden"}}>
      {/* Sidebar */}
      <aside style={{
        width:sidebarWidth, background:"#0B0F19",
        display:"flex", flexDirection:"column", flexShrink:0,
        transition:"width 0.2s ease", overflow:"hidden",
        borderRight:"1px solid rgba(255,255,255,0.08)",
      }}>
        {/* Logo area */}
        <div style={{padding:"16px 12px",borderBottom:"1px solid rgba(255,255,255,0.06)",
          display:"flex",alignItems:"center",justifyContent:"space-between",flexShrink:0}}>
          <Link href="/dashboard" style={{textDecoration:"none",display:"flex",
            alignItems:"center",gap:10,overflow:"hidden"}}>
            {/* Claustor SVG Logo Mark */}
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" style={{flexShrink:0}}>
              {/* Outer C arc */}
              <path d="M28 8C24.5 5.5 20 4 15 4C8.4 4 3 9.4 3 18s5.4 14 12 14c5 0 9.5-1.5 13-4"
                stroke="url(#cGrad)" strokeWidth="4" strokeLinecap="round" fill="none"/>
              {/* Circuit nodes */}
              <circle cx="28" cy="8" r="2.5" fill="#06B6D4"/>
              <circle cx="28" cy="28" r="2.5" fill="#06B6D4"/>
              <line x1="28" y1="8" x2="33" y2="8" stroke="#06B6D4" strokeWidth="1.5"/>
              <circle cx="33" cy="8" r="1.5" fill="#06B6D4"/>
              <line x1="28" y1="28" x2="33" y2="28" stroke="#06B6D4" strokeWidth="1.5"/>
              <circle cx="33" cy="28" r="1.5" fill="#06B6D4"/>
              {/* Document inside */}
              <rect x="11" y="11" width="11" height="14" rx="1.5" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.2)" strokeWidth="0.75"/>
              <line x1="13" y1="15" x2="20" y2="15" stroke="rgba(255,255,255,0.4)" strokeWidth="0.75"/>
              <line x1="13" y1="18" x2="20" y2="18" stroke="rgba(255,255,255,0.4)" strokeWidth="0.75"/>
              <line x1="13" y1="21" x2="18" y2="21" stroke="#06B6D4" strokeWidth="0.75"/>
              <defs>
                <linearGradient id="cGrad" x1="3" y1="4" x2="28" y2="32" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#5B4BFF"/>
                  <stop offset="100%" stopColor="#06B6D4"/>
                </linearGradient>
              </defs>
            </svg>
            {!collapsed && (
              <div style={{overflow:"hidden"}}>
                <div style={{color:"white",fontWeight:800,fontSize:16,letterSpacing:"-0.01em",
                  lineHeight:1.1}}>
                  <span style={{color:"#06B6D4"}}>C</span>laustor
                </div>
                <div style={{fontSize:11,color:"#94A3B8",marginTop:2,fontWeight:400}}>
                  AI Contract Intelligence
                </div>
              </div>
            )}
          </Link>
          {/* Collapse toggle */}
          <button onClick={()=>setCollapsed(!collapsed)}
            style={{background:"none",border:"none",borderRadius:6,
              padding:"6px",cursor:"pointer",color:"#64748B",
              display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,
              transition:"color 0.15s"}}
            onMouseEnter={e=>(e.currentTarget as HTMLElement).style.color="#CBD5E1"}
            onMouseLeave={e=>(e.currentTarget as HTMLElement).style.color="#64748B"}>
            {collapsed
              ? <ChevronRight size={14}/>
              : <ChevronLeft size={14}/>}
          </button>
        </div>

        {/* Nav */}
        <nav style={{padding:"8px 8px",flex:1,overflowY:"auto"}}>
          {/* Main section */}
          {!collapsed && (
            <div style={{fontSize:10,fontWeight:600,color:"#64748B",
              padding:"10px 12px 6px",letterSpacing:"0.08em",textTransform:"uppercase"}}>
              Main
            </div>
          )}
          {visibleNav.map(item=>{
            const active = isActive(item.href);
            const { Icon } = item;
            return (
              <Link key={item.href} href={item.href}
                title={collapsed?item.label:undefined}
                style={{
                  display:"flex",alignItems:"center",
                  gap:collapsed?0:12,
                  padding:collapsed?"10px":"9px 10px",
                  borderRadius:8,textDecoration:"none",
                  fontSize:14,marginBottom:2,fontWeight:active?600:500,
                  color:active?"white":"#94A3B8",
                  background:active?"rgba(99,102,241,0.15)":"transparent",
                  borderLeft:active?"3px solid #6366F1":"3px solid transparent",
                  justifyContent:collapsed?"center":"flex-start",
                  transition:"all 0.15s",
                }}
                onMouseEnter={e=>{
                  const el = e.currentTarget as HTMLElement;
                  if(!active){el.style.background="rgba(255,255,255,0.05)";el.style.color="white";}
                }}
                onMouseLeave={e=>{
                  const el = e.currentTarget as HTMLElement;
                  if(!active){el.style.background="transparent";el.style.color="#94A3B8";}
                }}>
                <Icon size={18} style={{flexShrink:0,color:active?"white":"#64748B"}}/>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}

          {/* Admin section */}
          {/* Locked main nav items */}
          {!collapsed && NAV_ITEMS.filter(item=>
            item.permission && !hasPermission(user.role, item.permission, user.plan)
          ).map(item=>{
            const { Icon } = item;
            const lockInfo = LOCKED_FEATURES[item.permission!];
            return (
              <button key={item.href}
                onClick={()=>lockInfo&&setUpgradeModal({feature:item.permission!,plan:lockInfo.plan})}
                style={{display:"flex",alignItems:"center",gap:12,
                  padding:"9px 10px",borderRadius:8,border:"none",
                  fontSize:14,marginBottom:2,fontWeight:400,
                  color:"rgba(255,255,255,0.2)",background:"transparent",
                  cursor:"pointer",width:"100%",textAlign:"left"}}>
                <Icon size={16} style={{flexShrink:0,color:"rgba(255,255,255,0.15)"}}/>
                <span style={{flex:1}}>{item.label}</span>
                <span style={{fontSize:9}}>🔒</span>
              </button>
            );
          })}
          {visibleAdmin.length > 0 && (
            <>
              {!collapsed && (
                <div style={{fontSize:10,fontWeight:600,color:"#64748B",
                  padding:"16px 12px 6px",letterSpacing:"0.08em",textTransform:"uppercase"}}>
                  Admin
                </div>
              )}
              {!collapsed && <div style={{height:1,background:"rgba(255,255,255,0.06)",margin:"0 10px 8px"}}/>}
              {visibleAdmin.map(item=>{
                const active = isActive(item.href);
                const { Icon } = item;
                return (
                  <Link key={item.href} href={item.href}
                    title={collapsed?item.label:undefined}
                    style={{
                      display:"flex",alignItems:"center",
                      gap:collapsed?0:12,
                      padding:collapsed?"10px":"9px 10px",
                      borderRadius:8,textDecoration:"none",
                      fontSize:14,marginBottom:2,fontWeight:active?600:500,
                      color:active?"white":"#94A3B8",
                      background:active?"rgba(99,102,241,0.15)":"transparent",
                      justifyContent:collapsed?"center":"flex-start",
                      transition:"all 0.15s",
                    }}
                    onMouseEnter={e=>{
                      const el = e.currentTarget as HTMLElement;
                      if(!active){el.style.background="rgba(255,255,255,0.05)";el.style.color="white";}
                    }}
                    onMouseLeave={e=>{
                      const el = e.currentTarget as HTMLElement;
                      if(!active){el.style.background="transparent";el.style.color="#94A3B8";}
                    }}>
                    <Icon size={18} style={{flexShrink:0,color:active?"white":"#64748B"}}/>
                    {!collapsed && <span>{item.label}</span>}
                  </Link>
                );
              })}

          {/* Locked admin items */}
          {!collapsed && ADMIN_NAV.filter(item=>
            item.permission && !hasPermission(user.role, item.permission, user.plan)
          ).map(item=>{
            const { Icon } = item;
            const isBilling = item.href.includes("billing");
            const lockInfo = LOCKED_FEATURES[item.permission!];
            if (isBilling) return (
              <a key={item.href} href={item.href}
                style={{display:"flex",alignItems:"center",gap:12,
                  padding:"9px 10px",borderRadius:8,
                  fontSize:14,marginBottom:2,fontWeight:600,
                  color:"#00A3FF",background:"rgba(0,163,255,0.08)",
                  border:"1px solid rgba(0,163,255,0.15)",
                  textDecoration:"none",transition:"all 0.15s"}}>
                <Icon size={16} style={{flexShrink:0,color:"#00A3FF"}}/>
                <span style={{flex:1}}>Billing</span>
                <span style={{fontSize:9,fontWeight:700,padding:"1px 5px",
                  borderRadius:4,background:"rgba(0,163,255,0.2)",
                  color:"#00A3FF"}}>UPGRADE</span>
              </a>
            );
            return (
              <button key={item.href}
                onClick={()=>lockInfo&&setUpgradeModal({feature:item.permission!,plan:lockInfo.plan})}
                style={{display:"flex",alignItems:"center",gap:12,
                  padding:"9px 10px",borderRadius:8,border:"none",
                  fontSize:14,marginBottom:2,fontWeight:400,
                  color:"rgba(255,255,255,0.2)",background:"transparent",
                  cursor:"pointer",width:"100%",textAlign:"left"}}
                onMouseEnter={e=>{
                  (e.currentTarget as HTMLElement).style.background="rgba(255,255,255,0.03)";
                  (e.currentTarget as HTMLElement).style.color="rgba(255,255,255,0.3)";
                }}
                onMouseLeave={e=>{
                  (e.currentTarget as HTMLElement).style.background="transparent";
                  (e.currentTarget as HTMLElement).style.color="rgba(255,255,255,0.2)";
                }}>
                <Icon size={16} style={{flexShrink:0,color:"rgba(255,255,255,0.15)"}}/>
                <span style={{flex:1}}>{item.label}</span>
                <span style={{fontSize:9}}>🔒</span>
              </button>
            );
          })}

            </>
          )}
        </nav>

        {/* Footer — Plan card + User card */}
        <div style={{padding:"12px 8px 16px",borderTop:"1px solid rgba(30,41,59,0.8)",flexShrink:0}}>
          {!collapsed && (
            <>
              {/* Plan card */}
              <div style={{padding:"10px 12px",borderRadius:8,marginBottom:6,
                background:"rgba(79,70,229,0.1)",
                border:"1px solid rgba(99,102,241,0.3)"}}>
                <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:2}}>
                  <span style={{fontSize:10}}>⚡</span>
                  <span style={{fontSize:10,fontWeight:700,letterSpacing:"0.08em",
                    textTransform:"uppercase",
                    color:planBadgeColor[user.plan]||"#6B7280"}}>
                    {user.plan} Plan
                  </span>
                </div>
                <div style={{fontSize:11,color:"rgba(255,255,255,0.4)"}}>
                  Contract intelligence active
                </div>
              </div>

              {/* User card */}
              <div style={{padding:"10px 12px",borderRadius:12,
                background:"rgba(15,23,42,0.6)",
                border:"1px solid rgba(255,255,255,0.06)"}}>
                <div style={{display:"flex",alignItems:"center",gap:8}}>
                  <div style={{width:28,height:28,borderRadius:"50%",
                    background:"linear-gradient(135deg,#5B4BFF,#06B6D4)",
                    display:"flex",alignItems:"center",justifyContent:"center",
                    color:"white",fontWeight:700,fontSize:12,flexShrink:0}}>
                    {user.email.charAt(0).toUpperCase()}
                  </div>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{color:"white",fontSize:12,fontWeight:600,
                      overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                      {user.email.split("@")[0]}
                    </div>
                    <div style={{color:"rgba(255,255,255,0.35)",fontSize:10}}>
                      {user.role.replace(/_/g," ")}
                    </div>
                  </div>
                  <button onClick={logout} title="Sign out"
                    style={{background:"none",border:"none",cursor:"pointer",
                      color:"rgba(255,255,255,0.3)",padding:4,
                      display:"flex",alignItems:"center"}}>
                    <LogOut size={13}/>
                  </button>
                </div>
              </div>
            </>
          )}

          {/* Collapsed: just avatar */}
          {collapsed && (
            <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:8,padding:"4px 0"}}>
              <div style={{width:32,height:32,borderRadius:"50%",
                background:"linear-gradient(135deg,#5B4BFF,#06B6D4)",
                display:"flex",alignItems:"center",justifyContent:"center",
                color:"white",fontWeight:700,fontSize:14}}>
                {user.email.charAt(0).toUpperCase()}
              </div>
              <button onClick={logout} title="Sign out"
                style={{background:"none",border:"none",cursor:"pointer",
                  color:"rgba(255,255,255,0.3)",padding:4}}>
                <LogOut size={13}/>
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main content area with top header */}
      <div style={{flex:1,display:"flex",flexDirection:"column",overflow:"hidden"}}>
        {/* Top header bar */}
{/* Top header bar */}
<header style={{
  height: 56,
  background: "white",
  borderBottom: "1px solid #E5E7EB",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "0 20px",
  gap: 12,
  flexShrink: 0,
  position: "sticky",
  top: 0,
  zIndex: 40,
}}>

  {/* Left: Breadcrumb */}
  <div style={{
    display: "flex", alignItems: "center", gap: 6,
    fontSize: 12, color: "#94A3B8", minWidth: "max-content",
  }}>
    <span
      onClick={() => router.push("/dashboard")}
      style={{ color: "#94A3B8", cursor: "pointer" }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = "#0066FF"}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = "#94A3B8"}
    >Dashboard</span>
    {pathname !== "/dashboard" && (
      <>
        <span style={{ color: "#D1D5DB" }}>/</span>
        <span style={{ fontWeight: 600, color: "#111827" }}>
          {(() => {
            const parts = pathname.split("/").filter(Boolean);
            // Skip UUIDs (contain dashes and are long)
            const label = parts.filter(p => 
              !p.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i) &&
              !p.match(/^[0-9a-f]{32}$/i)
            ).pop();
            const map: Record<string,string> = {
              contracts:"Contracts", copilot:"AI Copilot", analytics:"Analytics",
              settings:"Settings", reviews:"Reviews", obligations:"Obligations",
              compare:"Compare", bulk:"Bulk Import", admin:"Admin", playbook:"Playbook",
            };
            return map[label||""] || label?.replace(/-/g," ").replace(/\b\w/g, c => c.toUpperCase()) || "";
          })()}
        </span>
      </>
    )}
  </div>

  {/* Center: Command Palette trigger */}
  <div style={{ flex: 1, maxWidth: 420, margin: "0 auto" }}>
    <CommandPalette />
  </div>

  {/* Right: Upload + Notifications + Profile */}
  <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: "max-content" }}>

    {/* Upload contract button */}
    <button
      onClick={() => setShowUpload(true)}
      title="Upload contract"
      style={{
        width: 36, height: 36, borderRadius: 10,
        background: "#0066FF", color: "white",
        border: "none", cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: "0 1px 3px rgba(0,102,255,0.3)",
        flexShrink: 0,
      }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "#0052CC"}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "#0066FF"}
    >
      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
      </svg>
    </button>

    <div style={{ width: 1, height: 20, background: "#E5E7EB" }} />

    {/* Background processing indicator */}
    {bgJob && !bgJob.done && (
      <div
        onClick={() => setShowUpload(true)}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "5px 10px", borderRadius: 8,
          background: "#EFF6FF", border: "1px solid #DBEAFE",
          cursor: "pointer", fontSize: 11, color: "#0066FF",
          fontWeight: 600,
        }}
      >
        <div style={{
          width: 8, height: 8, borderRadius: "50%",
          border: "2px solid #0066FF", borderTopColor: "transparent",
          animation: "spin 0.6s linear infinite",
        }} />
        Analyzing...
      </div>
    )}
    {bgJob && bgJob.done && (
      <div
        onClick={() => { router.push(`/dashboard/contracts/${bgJob.contractId}`); setBgJob(null); }}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "5px 10px", borderRadius: 8,
          background: "#F0FDF4", border: "1px solid #BBF7D0",
          cursor: "pointer", fontSize: 11, color: "#16A34A",
          fontWeight: 600,
        }}
      >
        ✓ Analysis complete — View
      </div>
    )}
    {/* Notifications */}
    <NotificationBell />

    {/* Profile avatar */}
    <div
      onClick={() => setShowProfile(p => !p)}
      style={{
        width: 30, height: 30, borderRadius: "50%",
        background: "linear-gradient(135deg,#5B4BFF,#06B6D4)",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "white", fontWeight: 700, fontSize: 12, cursor: "pointer",
        boxShadow: "0 0 0 2px white, 0 0 0 3px #E2E8F0",
        position: "relative",
      }}>
      {user?.email?.charAt(0)?.toUpperCase() || "U"}
    </div>
    {showProfile && <ProfilePopup onClose={() => setShowProfile(false)} />}
  </div>
</header>

        <main style={{flex:1,overflowY:"auto",background:C.bg}}>
          {children}
        </main>
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onBackground={(cid, name) => { console.log("BG JOB:", cid, name); setBgJob({contractId:cid, fileName:name, done:false}); }} />}
    </div>
  );
}
