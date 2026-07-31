"use client";
import { useEffect, useState } from "react";
import { billing as billingAPI, getToken } from "@/lib/api";
import {
  Factory, Users, Scale, Pill, Landmark, Home, FileText, Cpu,
  CheckCircle, XCircle, Lock, Download, AlertCircle, Calendar,
  CreditCard, ChevronDown, ChevronUp, Plus, Shield, Zap,
  Eye, Database, Globe, Clock, BarChart2, Upload,
} from "lucide-react";

const API = "http://localhost:8000";
const C = {
  primary:"#0066FF", primaryLight:"#E6F0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  success:"#22C55E", warning:"#F59E0B", error:"#EF4444",
};
const GST = 0.18;

function formatStorage(mb: number): string {
  return mb >= 1024 ? `${(mb/1024).toFixed(0)} GB` : `${mb} MB`;
}
function formatUsed(used: number, limit: number, key: string): string {
  if (key === "storage_mb") return `${formatStorage(used)} / ${formatStorage(limit)}`;
  return `${used.toLocaleString()} / ${limit === -1 ? "∞" : limit.toLocaleString()}`;
}
function usageColor(pct: number): string {
  if (pct >= 90) return C.error;
  if (pct >= 70) return C.warning;
  return C.success;
}

const INDUSTRIES = [
  {id:"general",       Icon:FileText,  label:"General / Other",        desc:"Standard analysis"},
  {id:"it_saas",       Icon:Cpu,       label:"IT / SaaS",              desc:"SLA, IP, vendor lock-in"},
  {id:"manufacturing", Icon:Factory,   label:"Manufacturing",          desc:"Quality, force majeure"},
  {id:"hr_employment", Icon:Users,     label:"HR / Employment",        desc:"Non-compete, IP, termination"},
  {id:"legal",         Icon:Scale,     label:"Legal / Professional",   desc:"Retainer, conflicts"},
  {id:"real_estate",   Icon:Home,      label:"Real Estate / Lease",    desc:"Rent escalation, exits"},
  {id:"pharma",        Icon:Pill,      label:"Pharma / Life Sciences", desc:"FDA, IP, clinical"},
  {id:"banking",       Icon:Landmark,  label:"Banking / Finance",      desc:"RBI/SEBI, AML"},
];

// ── Complete feature matrix per plan ─────────────────────────────────────────
const PLAN_FEATURES: Record<string, {
  sections: {title:string; Icon:any; items:{label:string; included:boolean|"addon"}[]}[]
}> = {
  free: { sections: [
    { title:"Core", Icon:Zap, items:[
      {label:"5 contracts/month",           included:true},
      {label:"100 AI queries/month",        included:true},
      {label:"1 user",                      included:true},
      {label:"Basic clause extraction",     included:true},
      {label:"PDF/DOCX support",            included:true},
      {label:"Risk scoring",                included:true},
      {label:"AI Copilot chat",             included:true},
      {label:"Bulk import",                 included:false},
      {label:"Review workflow",             included:false},
    ]},
    { title:"AI Features", Icon:BarChart2, items:[
      {label:"10 clause types",             included:true},
      {label:"25 clause types",             included:false},
      {label:"Playbook similarity",         included:false},
      {label:"Missing clause detection",    included:false},
      {label:"Clause relationships",        included:false},
      {label:"Language detection",          included:false},
    ]},
    { title:"Security", Icon:Shield, items:[
      {label:"Org-level isolation",         included:true},
      {label:"AES-256 encryption",          included:true},
      {label:"Audit log",                   included:false},
      {label:"Data export (GDPR)",          included:false},
      {label:"SSO / SAML",                  included:false},
    ]},
    { title:"Industry Intelligence", Icon:Globe, items:[
      {label:"General industry only",       included:true},
      {label:"IT/SaaS, Manufacturing",      included:false},
      {label:"All 8 industries",            included:false},
      {label:"Custom clause weights",       included:false},
    ]},
  ]},
  starter: { sections: [
    { title:"Core", Icon:Zap, items:[
      {label:"100 contracts/month",         included:true},
      {label:"5,000 AI queries/month",      included:true},
      {label:"5 users",                     included:true},
      {label:"PDF/DOCX/Excel/XML support",  included:true},
      {label:"OCR for scanned PDFs",        included:true},
      {label:"Table extraction",            included:true},
      {label:"Obligation tracking",         included:true},
      {label:"Review workflow",             included:true},
      {label:"Bulk import",                 included:false},
    ]},
    { title:"AI Features", Icon:BarChart2, items:[
      {label:"25 clause types",             included:true},
      {label:"Risk scoring 0-100",          included:true},
      {label:"Playbook similarity",         included:true},
      {label:"Missing clause detection",    included:true},
      {label:"Clause relationships",        included:true},
      {label:"Language detection (5 lang)", included:true},
      {label:"Dedicated processing queue",  included:false},
    ]},
    { title:"Security", Icon:Shield, items:[
      {label:"Org-level isolation",         included:true},
      {label:"AES-256 encryption",          included:true},
      {label:"Audit log",                   included:true},
      {label:"Data export (GDPR)",          included:true},
      {label:"SSO / SAML",                  included:false},
      {label:"On-premise deployment",       included:false},
    ]},
    { title:"Industry Intelligence", Icon:Globe, items:[
      {label:"IT/SaaS industry scoring",   included:"addon"},
      {label:"Manufacturing scoring",      included:"addon"},
      {label:"HR / Employment scoring",    included:false},
      {label:"Pharma / Banking scoring",   included:false},
      {label:"Custom clause weights",      included:false},
    ]},
  ]},
  professional: { sections: [
    { title:"Core", Icon:Zap, items:[
      {label:"1,000 contracts/month",       included:true},
      {label:"50,000 AI queries/month",     included:true},
      {label:"25 users",                    included:true},
      {label:"All file formats + OCR",      included:true},
      {label:"Bulk import",                 included:true},
      {label:"Review workflow",             included:true},
      {label:"Webhooks & API access",       included:true},
      {label:"Dedicated processing queue",  included:true},
      {label:"PII masking (Presidio AI)",   included:true},
    ]},
    { title:"AI Features", Icon:BarChart2, items:[
      {label:"25 clause types",             included:true},
      {label:"Risk scoring 0-100",          included:true},
      {label:"Playbook similarity",         included:true},
      {label:"Industry risk weights",       included:true},
      {label:"Missing clause detection",    included:true},
      {label:"Clause relationships",        included:true},
      {label:"Language detection (5 lang)", included:true},
      {label:"Image recognition (OCR+AI)", included:true},
    ]},
    { title:"Security & Compliance", Icon:Shield, items:[
      {label:"Org-level isolation",         included:true},
      {label:"AES-256 encryption",          included:true},
      {label:"Audit log + data export",     included:true},
      {label:"GDPR data portability",       included:true},
      {label:"India data residency",        included:true},
      {label:"SSO / SAML",                  included:false},
      {label:"On-premise deployment",       included:false},
      {label:"VAPT / SOC2 report",          included:false},
    ]},
    { title:"Industry Intelligence", Icon:Globe, items:[
      {label:"All 8 industries (add-on)",   included:"addon"},
      {label:"Custom clause weights",       included:"addon"},
      {label:"Priority industry queue",     included:"addon"},
      {label:"Dedicated playbooks",         included:"addon"},
    ]},
  ]},
  enterprise: { sections: [
    { title:"Core", Icon:Zap, items:[
      {label:"Unlimited contracts",         included:true},
      {label:"Unlimited AI queries",        included:true},
      {label:"Unlimited users",             included:true},
      {label:"All Professional features",   included:true},
      {label:"Custom contract volume SLA",  included:true},
      {label:"White-label option",          included:true},
    ]},
    { title:"AI Features", Icon:BarChart2, items:[
      {label:"All AI features",             included:true},
      {label:"Custom clause taxonomy",      included:true},
      {label:"Custom risk weights",         included:true},
      {label:"Fine-tuned models",           included:true},
    ]},
    { title:"Security & Compliance", Icon:Shield, items:[
      {label:"All security features",       included:true},
      {label:"SSO / SAML / Auth0",          included:true},
      {label:"On-premise deployment",       included:true},
      {label:"VAPT report",                 included:true},
      {label:"SOC2 Type II report",         included:true},
      {label:"Custom DPA",                  included:true},
    ]},
    { title:"Industry Intelligence", Icon:Globe, items:[
      {label:"All 8 industries included",   included:true},
      {label:"Custom industry weights",     included:true},
      {label:"Bespoke playbooks",           included:true},
    ]},
  ]},
};

const PLANS = [
  {id:"free",         label:"Free",         base:0,     addon:0,    tagline:"Get started"},
  {id:"starter",      label:"Starter",      base:3999,  addon:1000, tagline:"For small teams",        addonLabel:"Industry Pack"},
  {id:"professional", label:"Professional", base:16499, addon:2500, tagline:"For growing businesses", addonLabel:"Pro Industry Add-on", popular:true},
  {id:"enterprise",   label:"Enterprise",   base:0,     addon:0,    tagline:"For large organisations"},
];
const PLAN_ORDER = ["free","starter","professional","enterprise"];

// ── Plan Feature Card ─────────────────────────────────────────────────────────
function PlanCard({ plan, isCurrent, isUpgrade, isDowngrade, onAction, upgrading }: any) {
  const [expanded, setExpanded] = useState(false);
  const features = PLAN_FEATURES[plan.id];

  return (
    <div style={{
      background:isCurrent?`linear-gradient(135deg,${C.primary}06,${C.primary}02)`:C.surface,
      border:`${isCurrent?"2px":"1px"} solid ${isCurrent?C.primary:C.border}`,
      borderRadius:14, display:"flex", flexDirection:"column", gap:0,
      position:"relative", overflow:"hidden",
    }}>
      {/* Banner */}
      {(isCurrent || plan.popular) && (
        <div style={{
          fontSize:9,fontWeight:700,padding:"4px 0",textAlign:"center",
          background:isCurrent?C.primary:"#F59E0B",color:"white",
          letterSpacing:"0.08em",
        }}>
          {isCurrent?"✓ CURRENT PLAN":"⭐ POPULAR"}
        </div>
      )}

      <div style={{padding:20,flex:1,display:"flex",flexDirection:"column",gap:14}}>
        {/* Plan name + price */}
        <div>
          <div style={{fontSize:15,fontWeight:800,color:C.heading,marginBottom:2}}>
            {plan.label}
          </div>
          <div style={{fontSize:11,color:C.muted,marginBottom:8}}>{plan.tagline}</div>
          <div style={{fontSize:20,fontWeight:900,
            color:isCurrent?C.primary:C.heading,letterSpacing:"-0.02em"}}>
            {plan.base > 0
              ? <>₹{plan.base.toLocaleString()}
                  <span style={{fontSize:10,fontWeight:400,color:C.muted}}>/mo + GST</span>
                </>
              : plan.id==="enterprise"
                ? <span style={{fontSize:14}}>Custom</span>
                : <span style={{color:C.success}}>Free</span>}
          </div>
          {plan.addon > 0 && (
            <div style={{fontSize:10,color:C.muted,marginTop:2}}>
              + ₹{plan.addon.toLocaleString()}/mo for industry pack
            </div>
          )}
        </div>

        {/* Quick features (top 4) */}
        <div style={{display:"flex",flexDirection:"column",gap:5}}>
          {features?.sections[0]?.items.slice(0,4).map((f:any)=>(
            <div key={f.label} style={{display:"flex",gap:6,
              alignItems:"center",fontSize:12}}>
              {f.included===true
                ? <CheckCircle size={11} style={{color:C.success,flexShrink:0}}/>
                : f.included==="addon"
                  ? <Plus size={11} style={{color:C.warning,flexShrink:0}}/>
                  : <XCircle size={11} style={{color:"#E5E7EB",flexShrink:0}}/>}
              <span style={{color:f.included?C.body:"#D1D5DB"}}>{f.label}</span>
            </div>
          ))}
        </div>

        {/* Expandable full features */}
        <button onClick={()=>setExpanded(!expanded)}
          style={{display:"flex",alignItems:"center",gap:6,
            background:"none",border:"none",cursor:"pointer",
            fontSize:12,color:C.primary,fontWeight:600,padding:0}}>
          {expanded ? <ChevronUp size={12}/> : <ChevronDown size={12}/>}
          {expanded ? "Hide features" : "See all features"}
        </button>

        {expanded && (
          <div style={{display:"flex",flexDirection:"column",gap:12,
            borderTop:`1px solid ${C.border}`,paddingTop:12}}>
            {features?.sections.map((section:any)=>(
              <div key={section.title}>
                <div style={{display:"flex",alignItems:"center",gap:6,
                  fontSize:10,fontWeight:700,color:C.muted,
                  textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:6}}>
                  <section.Icon size={10}/>
                  {section.title}
                </div>
                {section.items.map((item:any)=>(
                  <div key={item.label} style={{display:"flex",gap:6,
                    alignItems:"center",fontSize:12,marginBottom:4}}>
                    {item.included===true
                      ? <CheckCircle size={11} style={{color:C.success,flexShrink:0}}/>
                      : item.included==="addon"
                        ? <Plus size={11} style={{color:C.warning,flexShrink:0}}/>
                        : <XCircle size={11} style={{color:"#E5E7EB",flexShrink:0}}/>}
                    <span style={{
                      color:item.included===true?C.body:item.included==="addon"?C.warning:"#D1D5DB",
                      fontSize:11,
                    }}>
                      {item.label}
                      {item.included==="addon" && (
                        <span style={{fontSize:9,marginLeft:4,color:C.warning}}>(add-on)</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {/* CTA */}
        <div style={{marginTop:"auto"}}>
          {isCurrent ? (
            <div style={{padding:"9px",borderRadius:8,
              background:`${C.primary}10`,border:`1px solid ${C.primary}30`,
              fontSize:13,fontWeight:700,color:C.primary,textAlign:"center"}}>
              Active Plan ✓
            </div>
          ) : plan.id==="enterprise" ? (
            <a href="mailto:hello@claustor.ai"
              style={{padding:"9px",borderRadius:8,display:"block",
                border:`1.5px solid ${C.border}`,fontSize:13,fontWeight:600,
                color:C.body,textAlign:"center",textDecoration:"none"}}>
              Contact Sales
            </a>
          ) : isUpgrade ? (
            <button onClick={()=>onAction(plan.id,"upgrade")}
              disabled={upgrading===plan.id}
              style={{width:"100%",padding:"9px",borderRadius:8,
                background:C.primary,color:"white",border:"none",
                fontSize:13,fontWeight:700,cursor:"pointer",
                boxShadow:`0 2px 8px ${C.primary}30`}}>
              {upgrading===plan.id?"Upgrading...":"Upgrade →"}
            </button>
          ) : (
            <button onClick={()=>onAction(plan.id,"downgrade")}
              disabled={upgrading===plan.id}
              style={{width:"100%",padding:"9px",borderRadius:8,
                background:"transparent",color:C.muted,
                border:`1.5px solid ${C.border}`,
                fontSize:13,fontWeight:600,cursor:"pointer"}}>
              {upgrading===plan.id?"Processing...":"Downgrade"}
            </button>
          )}
        </div>
      </div>

    </div>
  );
}

export default function BillingPage() {
  const [summary, setSummary]           = useState<any>(null);
  const [invoices, setInvoices]         = useState<any[]>([]);
  const [orgInd, setOrgInd]             = useState<any>(null);
  const [addonEnabled, setAddonEnabled] = useState(false);
  const [addonPrompt, setAddonPrompt] = useState<{planId:string;action:string}|null>(null);
  const [addonChoice, setAddonChoice] = useState(false);
  const [loading, setLoading]           = useState(true);
  const [upgrading, setUpgrading]       = useState<string|null>(null);
  const [togglingAddon, setTogglingAddon] = useState(false);
  const [msg, setMsg]                   = useState("");

  const load = async () => {
    const token = getToken();
    const h = { Authorization: `Bearer ${token}` };
    try {
      const [s, inv, ind, aiRes, rzpPayments] = await Promise.all([
        billingAPI.summary(),
        billingAPI.invoices(),
        fetch(`${API}/api/v1/industries/org`, { headers: h }).then(r=>r.json()),
        fetch(`${API}/api/v1/observability/summary?days=30`, { headers: h }).then(r=>r.json()).catch(()=>null),
        fetch(`${API}/api/v1/billing/razorpay/payments`, { headers: h }).then(r=>r.json()).catch(()=>({payments:[]})),
      ]);
      setSummary(s);
      const rzpInvs = (rzpPayments?.payments||[]).map((p:any,i:number)=>({
        id: i,
        payment_id: p.id,
        order_id:   p.order_id,
        plan:        p.plan,
        addon:       p.addon,
        amount:      p.base_amount || (p.plan==="professional"?16499:3999),
        addon_amount:p.addon_amount || (p.addon?(p.plan==="professional"?2500:1000):0),
        gst_amount:  p.gst_amount  || 0,
        total_amount:p.total_amount || 0,
        status:      "paid",
        provider:    "razorpay",
        created_at:  p.created_at,
      }));
      const existingInvs = (inv as any).invoices || [];
      setInvoices([...rzpInvs, ...existingInvs]);
      setOrgInd(ind);
      setAddonEnabled(ind.addon_enabled || false);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(()=>{ load(); },[]);

  const toggleAddon = async (enabled: boolean) => {
    setTogglingAddon(true); setMsg("");
    const token = getToken();
    try {
      const r = await fetch(`${API}/api/v1/industries/org/addon`, {
        method:"POST",
        headers:{ Authorization:`Bearer ${token}`, "Content-Type":"application/json" },
        body: JSON.stringify({ addon_enabled: enabled }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail);
      setAddonEnabled(enabled);
      setMsg(`✅ ${d.message}`);
      await load();
    } catch(e: any) { setMsg(`❌ ${e.message}`); }
    finally { setTogglingAddon(false); }
  };

  // Load Razorpay checkout.js
  const loadRazorpay = (): Promise<boolean> =>
    new Promise(res=>{
      if ((window as any).Razorpay) return res(true);
      const s = document.createElement("script");
      s.src = "https://checkout.razorpay.com/v1/checkout.js";
      s.onload=()=>res(true); s.onerror=()=>res(false);
      document.body.appendChild(s);
    });

  const startPlanAction = (planId: string, action: string) => {
    if (planId === "free" || action === "downgrade") {
      handlePlanAction(planId, action, false);
      return;
    }
    // Show addon prompt for paid plan upgrades
    const plan = PLANS.find(p=>p.id===planId);
    if (plan && plan.addon > 0) {
      setAddonChoice(false);
      setAddonPrompt({planId, action});
    } else {
      handlePlanAction(planId, action, false);
    }
  };

  const handlePlanAction = async (planId: string, action: string, includeAddon = false) => {
    setUpgrading(planId); setMsg("");
    const token = getToken();

    // Free plan downgrade — no payment needed
    if (planId === "free") {
      try {
        const r = await fetch(`${API}/api/v1/billing/upgrade`, {
          method:"POST",
          headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
          body: JSON.stringify({plan: planId}),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail);
        setMsg("✅ Downgraded to free plan.");
        setTimeout(()=>window.location.reload(), 1200);
      } catch(e:any){ setMsg(`❌ ${e.message}`); }
      finally{ setUpgrading(null); }
      return;
    }

    // Paid plan — use Razorpay
    try {
      const loaded = await loadRazorpay();
      if (!loaded) { setMsg("❌ Payment gateway failed to load"); setUpgrading(null); return; }

      const orderRes = await fetch(`${API}/api/v1/billing/razorpay/create-order`, {
        method:"POST",
        headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
        body: JSON.stringify({plan: planId, addon: includeAddon}),
      });
      if (!orderRes.ok) { setMsg("❌ Failed to create payment order"); setUpgrading(null); return; }
      const order = await orderRes.json();

      const options = {
        key:         order.key_id,
        amount:      order.amount,
        currency:    order.currency,
        name:        "Claustor AI",
        description: order.breakdown
          ? `${planId.charAt(0).toUpperCase()+planId.slice(1)} Plan — Base: ₹${order.breakdown.base.toLocaleString()} + GST (18%): ₹${order.breakdown.gst.toLocaleString()} = ₹${order.breakdown.total.toLocaleString()}`
          : `${planId.charAt(0).toUpperCase()+planId.slice(1)} Plan`,
        order_id:    order.order_id,
        prefill:     {email: summary?.email||""},
        theme:       {color:"#0066FF"},
        handler: async (resp: any) => {
          const verRes = await fetch(`${API}/api/v1/billing/razorpay/verify-payment`,{
            method:"POST",
            headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
            body: JSON.stringify({
              razorpay_order_id:   resp.razorpay_order_id,
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_signature:  resp.razorpay_signature,
              plan: planId, addon: includeAddon,
            }),
          });
          const ver = await verRes.json();
          if (ver.success) {
            setMsg("✅ Payment successful! Plan upgraded.");
            setTimeout(()=>window.location.reload(), 1500);
          } else {
            setMsg("❌ Payment verification failed. Contact support.");
          }
          setUpgrading(null);
        },
        modal: { ondismiss: ()=>{ setMsg("Payment cancelled."); setUpgrading(null); } },
      };
      const rzp = new (window as any).Razorpay(options);
      rzp.on("payment.failed",(e:any)=>{ setMsg(`❌ Payment failed: ${e.error.description}`); setUpgrading(null); });
      rzp.open();
      return; // don't setUpgrading(null) here — modal handles it
    } catch(e:any){
      setMsg(`❌ ${e.message}`);
      setUpgrading(null);
    }

    // Legacy fallback (should not reach here for paid plans)
    try {
      const r = await fetch(`${API}/api/v1/billing/upgrade`, {
        method:"POST",
        headers:{ Authorization:`Bearer ${token}`, "Content-Type":"application/json" },
        body: JSON.stringify({ plan: planId }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail);
      setMsg(`✅ ${d.message}`);
      await load();
    } catch(e: any) { setMsg(`❌ ${e.message}`); }
    finally { setUpgrading(null); }
  };

  const downloadInvoicePDF = async (idx: number) => {
    const token = getToken();
    const r = await fetch(`${API}/api/v1/billing/invoice/${idx}/pdf`,
      {headers:{Authorization:`Bearer ${token}`}});
    if (r.ok) {
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href=url; a.download=`claustor-invoice-${idx+1}.pdf`; a.click();
    } else { setMsg("❌ Invoice PDF generation failed"); }
  };

  const currentPlan     = summary?.plan || "free";
  const currentPlanObj  = PLANS.find(p=>p.id===currentPlan);
  const monthlyBase     = currentPlanObj?.base || 0;
  const monthlyAddon    = addonEnabled ? (currentPlanObj?.addon || 0) : 0;
  const monthlySubtotal = monthlyBase + monthlyAddon;
  const monthlyGST      = Math.round(monthlySubtotal * GST);
  const monthlyTotal    = monthlySubtotal + monthlyGST;
  const currentIdx      = PLAN_ORDER.indexOf(currentPlan);

  if (loading) return (
    <div style={{padding:60,textAlign:"center",color:C.muted}}>
      <div style={{width:32,height:32,borderRadius:"50%",
        border:`2px solid ${C.primary}`,borderTopColor:"transparent",
        animation:"spin 0.8s linear infinite",margin:"0 auto 12px"}}/>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  return (
    <div style={{padding:"32px 36px",maxWidth:1100,margin:"0 auto"}}>
      <div style={{marginBottom:24}}>
        <h1 style={{fontSize:22,fontWeight:800,color:C.heading,marginBottom:4}}>Billing & Plans</h1>
        <p style={{fontSize:13,color:C.muted}}>Manage your subscription, add-ons, and invoices</p>
      </div>

      {msg && (
        <div style={{padding:"12px 16px",borderRadius:8,marginBottom:16,
          background:msg.startsWith("✅")?"#F0FDF4":"#FEF2F2",
          color:msg.startsWith("✅")?C.success:C.error,fontSize:14}}>
          {msg}
        </div>
      )}

      {/* Current Plan */}
      {summary && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:14,padding:24,marginBottom:20}}>
          <div style={{display:"flex",justifyContent:"space-between",
            alignItems:"flex-start",marginBottom:24}}>
            <div>
              <div style={{fontSize:11,fontWeight:600,color:C.muted,
                textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:4}}>
                Current Plan
              </div>
              <div style={{fontSize:24,fontWeight:900,color:C.primary,
                textTransform:"capitalize",marginBottom:6}}>{currentPlan}</div>
              {addonEnabled && currentPlanObj?.addonLabel && (
                <div style={{display:"flex",alignItems:"center",gap:6,
                  fontSize:12,color:C.success,fontWeight:600}}>
                  <CheckCircle size={12}/> {currentPlanObj.addonLabel} active
                </div>
              )}
              {summary.next_billing_date && (
                <div style={{display:"flex",alignItems:"center",gap:6,
                  fontSize:12,color:C.muted,marginTop:6}}>
                  <Calendar size={12}/>
                  Next billing: {new Date(summary.next_billing_date)
                    .toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}
                </div>
              )}
            </div>
            {monthlySubtotal > 0 ? (
              <div style={{textAlign:"right",padding:"16px 20px",
                background:C.bg,borderRadius:10,border:`1px solid ${C.border}`}}>
                <div style={{fontSize:11,color:C.muted,marginBottom:8,fontWeight:600,
                  textTransform:"uppercase",letterSpacing:"0.06em"}}>Monthly Total</div>
                <div style={{display:"flex",flexDirection:"column",gap:3,
                  fontSize:12,color:C.muted,marginBottom:8}}>
                  <div style={{display:"flex",justifyContent:"space-between",gap:24}}>
                    <span>Base plan</span><span>₹{monthlyBase.toLocaleString()}</span>
                  </div>
                  {monthlyAddon>0 && (
                    <div style={{display:"flex",justifyContent:"space-between",gap:24}}>
                      <span>Industry add-on</span><span>₹{monthlyAddon.toLocaleString()}</span>
                    </div>
                  )}
                  <div style={{display:"flex",justifyContent:"space-between",gap:24}}>
                    <span>GST (18%)</span><span>₹{monthlyGST.toLocaleString()}</span>
                  </div>
                </div>
                <div style={{borderTop:`1px solid ${C.border}`,paddingTop:8}}>
                  <div style={{fontSize:22,fontWeight:900,color:C.heading}}>
                    ₹{monthlyTotal.toLocaleString()}
                    <span style={{fontSize:12,color:C.muted,fontWeight:400}}>/mo</span>
                  </div>
                  <div style={{fontSize:10,color:C.muted}}>incl. GST</div>
                </div>
              </div>
            ) : (
              <div style={{padding:"16px 24px",background:"#F0FDF4",
                borderRadius:10,border:"1px solid #22C55E30",textAlign:"center"}}>
                <div style={{fontSize:22,fontWeight:900,color:C.success}}>Free</div>
              </div>
            )}
          </div>

          {/* Usage bars */}
          {summary.usage && Object.entries(summary.usage).map(([k,v]:any)=>{
            const pct = Math.min(v.pct||0,100);
            const color = usageColor(pct);
            const label = k==="storage_mb"?"Storage":k==="ai_queries"?"AI Queries"
              :k.replace(/_/g," ").replace(/\b\w/g,(c:string)=>c.toUpperCase());
            return (
              <div key={k} style={{marginBottom:14}}>
                <div style={{display:"flex",justifyContent:"space-between",
                  fontSize:13,marginBottom:6,alignItems:"center"}}>
                  <span style={{fontWeight:500,color:C.body}}>{label}</span>
                  <div style={{display:"flex",alignItems:"center",gap:8}}>
                    <span style={{color:pct>70?color:C.muted,fontSize:12}}>
                      {formatUsed(v.used,v.limit,k)}
                    </span>
                    {pct>=90&&(
                      <span style={{fontSize:10,fontWeight:700,padding:"2px 8px",
                        borderRadius:20,background:"#FEF2F2",color:C.error,
                        display:"flex",alignItems:"center",gap:4}}>
                        <AlertCircle size={10}/> Upgrade
                      </span>
                    )}
                  </div>
                </div>
                <div style={{height:8,background:C.border,borderRadius:4,overflow:"hidden"}}>
                  <div style={{height:"100%",width:`${pct}%`,borderRadius:4,
                    background:color,transition:"width 0.5s ease"}}/>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Industry Add-on */}
      {currentPlanObj && (currentPlanObj as any).addon > 0 && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:14,padding:24,marginBottom:20}}>
          <div style={{display:"flex",justifyContent:"space-between",
            alignItems:"flex-start",marginBottom:16}}>
            <div>
              <div style={{fontSize:15,fontWeight:700,color:C.heading,marginBottom:4}}>
                Industry Risk Scoring
              </div>
              <div style={{fontSize:13,color:C.muted}}>
                Custom clause weights, priority processing, and 8 industry playbooks
                <span style={{color:C.warning,fontWeight:600}}>
                  {" "}(+₹{(currentPlanObj as any).addon.toLocaleString()}/mo + GST)
                </span>
              </div>
            </div>
            <div style={{display:"flex",alignItems:"center",gap:10}}>
              <span style={{fontSize:12,color:C.muted}}>
                {addonEnabled?"Active":"Inactive"}
              </span>
              <button onClick={()=>toggleAddon(!addonEnabled)}
                disabled={togglingAddon}
                style={{width:48,height:26,borderRadius:13,border:"none",
                  cursor:togglingAddon?"not-allowed":"pointer",
                  background:addonEnabled?C.success:"#D1D5DB",
                  position:"relative",transition:"background 0.2s"}}>
                <div style={{width:20,height:20,borderRadius:"50%",background:"white",
                  position:"absolute",top:3,left:addonEnabled?24:3,
                  transition:"left 0.2s",boxShadow:"0 1px 3px rgba(0,0,0,0.2)"}}/>
              </button>
            </div>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10}}>
            {INDUSTRIES.map(ind=>{
              const active = addonEnabled;
              return (
                <div key={ind.id} style={{padding:"12px",borderRadius:10,
                  background:active?`${C.primary}08`:C.bg,
                  border:`1px solid ${active?`${C.primary}30`:C.border}`,
                  opacity:active?1:0.6,transition:"all 0.2s"}}>
                  <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:6}}>
                    <div style={{width:24,height:24,borderRadius:6,
                      background:active?`${C.primary}15`:"#F3F4F6",
                      display:"flex",alignItems:"center",justifyContent:"center"}}>
                      <ind.Icon size={12} style={{color:active?C.primary:C.muted}}/>
                    </div>
                    <div style={{fontSize:11,fontWeight:700,
                      color:active?C.heading:C.muted,lineHeight:1.2}}>
                      {ind.label}
                    </div>
                  </div>
                  <div style={{display:"flex",alignItems:"center",gap:4}}>
                    {active
                      ? <><CheckCircle size={9} style={{color:C.success}}/>
                          <span style={{fontSize:10,fontWeight:600,color:C.success}}>Active</span></>
                      : <><Lock size={9} style={{color:C.muted}}/>
                          <span style={{fontSize:10,color:C.muted}}>Locked</span></>}
                  </div>
                </div>
              );
            })}
          </div>
          {!addonEnabled && (
            <div style={{marginTop:14,padding:"12px 16px",
              background:"#FFFBEB",border:"1px solid #F59E0B30",borderRadius:8,
              display:"flex",alignItems:"center",justifyContent:"space-between"}}>
              <span style={{fontSize:13,color:C.warning,fontWeight:600}}>
                🔓 Unlock all 8 industries
              </span>
              <button onClick={()=>toggleAddon(true)} disabled={togglingAddon}
                style={{padding:"6px 16px",background:C.warning,color:"white",
                  border:"none",borderRadius:8,fontSize:12,fontWeight:700,cursor:"pointer"}}>
                Enable +₹{(currentPlanObj as any).addon.toLocaleString()}/mo
              </button>
            </div>
          )}
        </div>
      )}

      {/* Available Plans */}
      <div style={{marginBottom:20}}>
        <h2 style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:16}}>
          Available Plans
        </h2>
        <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
          {PLANS.map(plan=>{
            const isCurrent  = plan.id===currentPlan;
            const planIdx    = PLAN_ORDER.indexOf(plan.id);
            const isUpgrade  = planIdx > currentIdx;
            const isDowngrade = planIdx < currentIdx;
            return (
              <PlanCard key={plan.id}
                plan={plan}
                isCurrent={isCurrent}
                isUpgrade={isUpgrade}
                isDowngrade={isDowngrade}
                onAction={startPlanAction}
                upgrading={upgrading}/>
            );
          })}
        </div>
        <p style={{fontSize:11,color:C.muted,marginTop:12,textAlign:"center"}}>
          ✅ = Included &nbsp;|&nbsp; ➕ = Available as add-on &nbsp;|&nbsp; ✕ = Not available &nbsp;|&nbsp; All prices + 18% GST
        </p>
      </div>

      {/* Invoice History */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,
        borderRadius:14,overflow:"hidden"}}>
        <div style={{padding:"16px 24px",borderBottom:`1px solid ${C.border}`,
          display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <h2 style={{fontSize:16,fontWeight:700,color:C.heading}}>Invoice History</h2>
          <span style={{fontSize:12,color:C.muted}}>All amounts include GST</span>
        </div>
        <div style={{display:"grid",
          gridTemplateColumns:"1fr 1fr 1fr 130px 90px 110px",
          padding:"10px 24px",background:C.bg,
          borderBottom:`1px solid ${C.border}`,fontSize:11,
          fontWeight:700,color:C.muted,textTransform:"uppercase",letterSpacing:"0.05em"}}>
          {["Period","Base Plan","Add-on","Total (incl. GST)","Status","Receipt"].map(h=>(
            <div key={h}>{h}</div>
          ))}
        </div>
        {invoices.length===0 ? (
          <div style={{padding:40,textAlign:"center",color:C.muted,fontSize:14}}>
            <CreditCard size={32} style={{margin:"0 auto 12px",opacity:0.3}}/>
            No invoices yet
          </div>
        ) : invoices.map((inv,i)=>(
          <div key={i} style={{display:"grid",
            gridTemplateColumns:"1fr 1fr 1fr 130px 90px 110px",
            padding:"14px 24px",borderBottom:`1px solid ${C.border}`,
            alignItems:"center",fontSize:13}}>
            <div style={{fontWeight:600,color:C.heading}}>
              {new Date(inv.period_start||inv.date||Date.now())
                .toLocaleDateString("en-IN",{month:"short",year:"numeric"})}
            </div>
            <div>₹{(inv.base_amount||inv.amount||0).toLocaleString()}</div>
            <div>{inv.addon_amount>0?`₹${inv.addon_amount.toLocaleString()}`:<span style={{color:C.muted}}>—</span>}</div>
            <div style={{fontWeight:700,color:C.heading}}>
              ₹{(inv.total_amount||inv.amount||0).toLocaleString()}
            </div>
            <div>
              <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:20,
                background:inv.status==="paid"?"#F0FDF4":"#FEF2F2",
                color:inv.status==="paid"?C.success:C.error}}>
                {inv.status==="paid"?"✓ Paid":"Pending"}
              </span>
            </div>
            <div>
              <button onClick={()=>downloadInvoicePDF(i)}
                style={{display:"flex",alignItems:"center",gap:5,
                  padding:"5px 10px",border:`1px solid ${C.border}`,
                  borderRadius:8,background:C.bg,cursor:"pointer",
                  fontSize:12,color:C.body,fontWeight:600}}>
                <Download size={11}/> PDF
              </button>
            </div>
          </div>
        ))}
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      {/* Addon Prompt Modal */}
      {addonPrompt && (
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",
          display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000}}>
          <div style={{background:"white",borderRadius:16,padding:28,
            maxWidth:420,width:"90%",boxShadow:"0 20px 60px rgba(0,0,0,0.2)"}}>
            <h3 style={{fontSize:17,fontWeight:800,color:"#111827",marginBottom:6}}>
              Add Industry Pack?
            </h3>
            <p style={{fontSize:13,color:"#6B7280",marginBottom:20}}>
              Enhance your plan with industry-specific clause scoring, playbooks, and risk benchmarks.
            </p>

            {/* Base plan */}
            <div style={{padding:"12px 16px",borderRadius:10,marginBottom:10,
              background:"#F8FAFC",border:"1px solid #E5E7EB"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                <div>
                  <div style={{fontSize:13,fontWeight:700,color:"#111827"}}>
                    {PLANS.find(p=>p.id===addonPrompt.planId)?.label} Plan
                  </div>
                  <div style={{fontSize:11,color:"#6B7280"}}>Base plan features</div>
                </div>
                <div style={{fontSize:15,fontWeight:700,color:"#0066FF"}}>
                  ₹{PLANS.find(p=>p.id===addonPrompt.planId)?.base.toLocaleString()}/mo
                </div>
              </div>
            </div>

            {/* Addon option */}
            <div onClick={()=>setAddonChoice(!addonChoice)}
              style={{padding:"12px 16px",borderRadius:10,marginBottom:16,
                background:addonChoice?"#EFF6FF":"#F8FAFC",
                border:`2px solid ${addonChoice?"#0066FF":"#E5E7EB"}`,
                cursor:"pointer",transition:"all 0.15s"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                <div style={{display:"flex",alignItems:"center",gap:10}}>
                  <div style={{width:20,height:20,borderRadius:5,
                    background:addonChoice?"#0066FF":"white",
                    border:`2px solid ${addonChoice?"#0066FF":"#D1D5DB"}`,
                    display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                    {addonChoice&&<span style={{color:"white",fontSize:12,fontWeight:900}}>✓</span>}
                  </div>
                  <div>
                    <div style={{fontSize:13,fontWeight:700,color:"#111827"}}>
                      Industry Pack Add-on
                    </div>
                    <div style={{fontSize:11,color:"#6B7280"}}>
                      8 industries · custom scoring · priority queue
                    </div>
                  </div>
                </div>
                <div style={{fontSize:14,fontWeight:700,color:"#F59E0B",flexShrink:0}}>
                  +₹{PLANS.find(p=>p.id===addonPrompt.planId)?.addon.toLocaleString()}/mo
                </div>
              </div>
            </div>

            {/* Total */}
            <div style={{padding:"10px 16px",borderRadius:8,marginBottom:20,
              background:"#F0FDF4",border:"1px solid #22C55E30"}}>
              <div style={{display:"flex",justifyContent:"space-between",fontSize:13}}>
                <span style={{color:"#6B7280"}}>Subtotal</span>
                <span style={{fontWeight:700,color:"#111827"}}>
                  ₹{((PLANS.find(p=>p.id===addonPrompt.planId)?.base||0) +
                     (addonChoice?(PLANS.find(p=>p.id===addonPrompt.planId)?.addon||0):0)
                    ).toLocaleString()}/mo
                </span>
              </div>
              <div style={{display:"flex",justifyContent:"space-between",fontSize:13,marginTop:4}}>
                <span style={{color:"#6B7280"}}>GST (18%)</span>
                <span style={{fontWeight:700,color:"#111827"}}>
                  ₹{Math.round(((PLANS.find(p=>p.id===addonPrompt.planId)?.base||0) +
                     (addonChoice?(PLANS.find(p=>p.id===addonPrompt.planId)?.addon||0):0)
                    ) * 0.18).toLocaleString()}/mo
                </span>
              </div>
              <div style={{display:"flex",justifyContent:"space-between",
                fontSize:15,fontWeight:800,marginTop:8,paddingTop:8,
                borderTop:"1px solid #E5E7EB"}}>
                <span style={{color:"#111827"}}>Total</span>
                <span style={{color:"#22C55E"}}>
                  ₹{Math.round(((PLANS.find(p=>p.id===addonPrompt.planId)?.base||0) +
                     (addonChoice?(PLANS.find(p=>p.id===addonPrompt.planId)?.addon||0):0)
                    ) * 1.18).toLocaleString()}/mo
                </span>
              </div>
            </div>

            <div style={{display:"flex",gap:10}}>
              <button onClick={()=>setAddonPrompt(null)}
                style={{flex:1,padding:"11px",border:"1px solid #E5E7EB",
                  borderRadius:10,background:"white",cursor:"pointer",
                  fontSize:13,color:"#6B7280",fontWeight:600}}>
                Cancel
              </button>
              <button onClick={()=>{
                const {planId,action}=addonPrompt;
                setAddonPrompt(null);
                handlePlanAction(planId, action, addonChoice);
              }}
                style={{flex:2,padding:"11px",border:"none",
                  borderRadius:10,background:"#0066FF",cursor:"pointer",
                  fontSize:13,color:"white",fontWeight:700}}>
                Proceed to Payment →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
