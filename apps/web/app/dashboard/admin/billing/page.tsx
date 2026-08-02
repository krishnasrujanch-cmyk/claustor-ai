"use client";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
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
  if (mb === -1) return "∞";
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
  {id:"enterprise",   label:"Enterprise",   base:-1,    addon:0,    tagline:"For large organisations"},
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
            {plan.base > 0 && plan.base !== -1
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
            <button onClick={()=>onAction(plan.id,"enterprise")}
              style={{padding:"9px",borderRadius:8,display:"block",width:"100%",
                border:`1.5px solid ${C.border}`,fontSize:13,fontWeight:600,
                color:C.body,textAlign:"center",background:"white",cursor:"pointer"}}>
              Contact Sales
            </button>
          ) : isUpgrade ? (
            <button onClick={()=>onAction(plan.id,"upgrade")}
              disabled={upgrading===plan.id}
              style={{width:"100%",padding:"9px",borderRadius:8,
                background:C.primary,color:"white",border:"none",
                fontSize:13,fontWeight:700,cursor:"pointer",
                boxShadow:`0 2px 8px ${C.primary}30`}}>
              {upgrading===plan.id?"Upgrading...":"Upgrade →"}
            </button>
          ) : isDowngrade && plan.id === "starter" && !isUpgrade ? (
            <button disabled
              style={{width:"100%",padding:"10px",border:"1px solid #E5E7EB",
                borderRadius:10,background:"#F9FAFB",cursor:"not-allowed",
                fontSize:13,color:"#9CA3AF",fontWeight:600}}>
              Not Available
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
  const router = useRouter();
  const { loadUser } = useAuthStore();
  const [addonEnabled, setAddonEnabled]   = useState(false);
  const [enterpriseModal, setEnterpriseModal] = useState(false);
  const [enterpriseForm, setEnterpriseForm]   = useState({business_name:"",industry:"",company_size:"",contact_name:"",business_email:"",mobile:"",contracts_per_month:"",message:""});
  const [enterpriseMsg, setEnterpriseMsg]     = useState("");
  const [enterpriseSending, setEnterpriseSending] = useState(false);
  const [addonModal, setAddonModal]       = useState<{planId:string;action:string}|null>(null);
  const [proRate, setProRate]             = useState<any>(null);
  const [addonSelected, setAddonSelected] = useState(false);
  const [periodSelected, setPeriodSelected] = useState<"monthly"|"6months"|"12months">("monthly");
  const [loading, setLoading]           = useState(true);
  const [upgrading, setUpgrading]       = useState<string|null>(null);
  const [togglingAddon, setTogglingAddon] = useState(false);
  const [msg, setMsg]                   = useState("");

  const load = async () => {
    const token = getToken();
    const h = { Authorization: `Bearer ${token}` };
    try {
      const [s, inv, ind, rzpPayments] = await Promise.all([
        billingAPI.summary(),
        billingAPI.invoices(),
        fetch(`${API}/api/v1/industries/org`, { headers: h }).then(r=>r.json()),
        fetch(`${API}/api/v1/billing/razorpay/payments`, { headers: h }).then(r=>r.ok?r.json():{payments:[]}).catch(()=>({payments:[]})),
      ]);
      setSummary(s);
      const rzpInvs = (rzpPayments?.payments||[]).map((p:any,idx:number)=>({
        id: idx, payment_id: p.id, order_id: p.order_id,
        plan: p.plan, addon: p.addon, period: p.period,
        base_amount:  p.base_amount  || 0,
        addon_amount: p.addon_amount || 0,
        gst_amount:   p.gst_amount   || 0,
        total_amount: p.total_amount || 0,
        amount:       p.total_amount || 0,
        status: "paid", provider:"razorpay",
        created_at: p.created_at,
      }));
      setInvoices([...rzpInvs, ...((inv as any).invoices||[])]);
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

  // Intercept plan upgrade to show addon+period popup
  const startPlanAction = (planId: string, action: string) => {
    if (planId === "enterprise") { setEnterpriseModal(true); return; }
    if (planId === "free" || action === "downgrade") {
      handlePlanAction(planId, action, false, "monthly");
      return;
    }
    setAddonSelected(false);
    setPeriodSelected("monthly");
    setProRate(null);
    setAddonModal({planId, action});
    // Fetch pro-rata credit if upgrading from starter
    if (planId === "professional") {
      const token = getToken();
      fetch(`${API}/api/v1/billing/razorpay/prorate?target_plan=professional&period=monthly&addon=${addonSelected}`, {
        headers: {Authorization: `Bearer ${token}`}
      }).then(r=>r.ok?r.json():null).then(d=>{ if(d) setProRate(d); }).catch(()=>{});
    }
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

  const handlePlanAction = async (planId: string, action: string, includeAddon = false, period: "monthly"|"6months"|"12months" = "monthly", proRateData: any = null) => {
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
        setTimeout(async()=>{ await loadUser(); router.refresh(); load(); }, 1200);
      } catch(e:any){ setMsg(`❌ ${e.message}`); }
      finally{ setUpgrading(null); }
      return;
    }

    // Paid plan — use Razorpay
    try {
      // Free upgrade — skip Razorpay
      if (proRateData?.free_upgrade) {
        try {
          const verRes = await fetch(`${API}/api/v1/billing/razorpay/verify-payment`, {
            method:"POST",
            headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
            body: JSON.stringify({
              razorpay_order_id:   "free_upgrade_" + Date.now(),
              razorpay_payment_id: "free_upgrade",
              razorpay_signature:  "free_upgrade",
              plan: planId, addon: includeAddon, period,
              total_amount: 0,
              free_upgrade: true,
              extended_days: proRateData.extended_days,
            }),
          });
          const ver = await verRes.json();
          if (ver.success) { setMsg("✅ Upgraded to Professional!"); setTimeout(async()=>{ await loadUser(); router.refresh(); load(); }, 1200); }
          else { setMsg("❌ Upgrade failed. Contact support."); }
        } catch(e) { setMsg("❌ Error during upgrade."); }
        finally { setUpgrading(null); }
        return;
      }

      const loaded = await loadRazorpay();
      if (!loaded) { setMsg("❌ Payment gateway failed to load"); setUpgrading(null); return; }

      const orderRes = await fetch(`${API}/api/v1/billing/razorpay/create-order`, {
        method:"POST",
        headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
        body: JSON.stringify({plan: planId, addon: includeAddon, period, apply_credit: true}),
      });
      if (!orderRes.ok) { setMsg("❌ Failed to create payment order"); setUpgrading(null); return; }
      const order = await orderRes.json();

      const options = {
        key:         order.key_id,
        amount:      order.amount,
        currency:    order.currency,
        name:        "Claustor AI",
        description: `${planId.charAt(0).toUpperCase()+planId.slice(1)} Plan`,
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
              period: period,
              total_amount: order.breakdown?.total || 0,
            }),
          });
          const ver = await verRes.json();
          if (ver.success) {
            setMsg("✅ Payment successful! Plan upgraded.");
            setTimeout(async()=>{ await loadUser(); router.refresh(); load(); }, 1200);
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

  const downloadInvoicePDF = (idx: number) => {
    const inv = invoices[idx];
    if (!inv) return;
    const COMPANY = {name:"DKU Technologies Pvt. Ltd.",brand:"Claustor AI",email:"info@claustor.com",website:"claustor.ai",gstin:"36AATFD9569L1ZC",address:"Hyderabad, Telangana, India"};
    const base   = (()=>{const b=inv.base_amount||0;return b>100000?Math.round(b/100):b;})();
    const addon  = (()=>{const a=inv.addon_amount||0;return a>100000?Math.round(a/100):a;})();
    const credit = inv.credit_applied||0;
    const gst    = inv.gst_amount||Math.round((base+addon-credit)*0.18);
    const total  = (()=>{const t=inv.total_amount||inv.amount||0;return t>100000?Math.round(t/100):t;})();
    const planLabel=inv.plan?inv.plan.charAt(0).toUpperCase()+inv.plan.slice(1):"Plan";
    const period=inv.period==="12months"?"12 Months (10 charged, 2 free)":inv.period==="6months"?"6 Months (5 charged, 1 free)":"Monthly";
    const date=new Date(inv.created_at||Date.now());
    const dateStr=date.toLocaleDateString("en-IN",{day:"2-digit",month:"long",year:"numeric"});
    const invoiceNo=`CLST-${date.getFullYear()}-${String(idx+1).padStart(4,"0")}`;
    const cgst=Math.round(gst/2); const sgst=Math.round(gst/2);
    const html=`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Invoice ${invoiceNo}</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Helvetica Neue',Arial,sans-serif;color:#111827;padding:0}.page{max-width:680px;margin:0 auto;padding:48px}
.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px;padding-bottom:28px;border-bottom:2px solid #0066FF}
.logo-name{font-size:22px;font-weight:900;color:#0A1128;letter-spacing:-0.5px}.logo-icon{display:inline-flex;width:40px;height:40px;border-radius:10px;align-items:center;justify-content:center;margin-right:10px;vertical-align:middle;background:#F0F7FF}
.company-detail{font-size:11px;color:#6B7280;line-height:1.7;margin-top:6px}
.invoice-title{font-size:26px;font-weight:900;color:#0A1128;letter-spacing:-1px}.invoice-sub{font-size:12px;color:#6B7280;margin-top:4px}.badge{display:inline-block;background:#F0FDF4;color:#16A34A;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;border:1px solid #BBF7D0;margin-top:8px}
.plan-box{background:linear-gradient(135deg,#EFF6FF,#F0F9FF);border:1px solid #BFDBFE;border-radius:12px;padding:20px 24px;margin-bottom:28px;display:flex;justify-content:space-between;align-items:center}
.plan-name{font-size:17px;font-weight:800;color:#0A1128}.plan-period{font-size:12px;color:#6B7280;margin-top:2px}.plan-tag{font-size:10px;font-weight:700;color:#0066FF;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px}
.plan-total{font-size:26px;font-weight:900;color:#0066FF;text-align:right}.plan-total-label{font-size:11px;color:#6B7280;text-align:right;margin-top:2px}
.section-label{font-size:10px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px}
table{width:100%;border-collapse:collapse;margin-bottom:20px}
thead th{background:#F8FAFC;padding:9px 14px;text-align:left;font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;letter-spacing:0.05em}
thead th:last-child{text-align:right}
tbody td{padding:11px 14px;border-bottom:1px solid #F1F5F9;font-size:13px;color:#374151}
tbody td:last-child{text-align:right;font-weight:600}
.credit-row td{color:#16A34A}.muted-row td{color:#9CA3AF;font-size:12px}
.total-row{background:#0A1128}.total-row td{padding:14px 16px;font-size:15px;font-weight:800;color:white;border:none}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:28px}
.info-box{border:1px solid #E5E7EB;border-radius:8px;padding:14px 16px}
.info-title{font-size:10px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px}
.info-val{font-size:13px;color:#111827;line-height:1.6}
.footer{padding-top:20px;border-top:1px solid #E5E7EB;display:flex;justify-content:space-between;align-items:flex-end}
.footer-left{font-size:11px;color:#9CA3AF;line-height:1.6}.footer-right{font-size:10px;color:#D1D5DB;text-align:right}
@media print{body{print-color-adjust:exact;-webkit-print-color-adjust:exact}}</style></head>
<body><div class="page">
<div class="header">
  <div>
    <div><span class="logo-icon"><svg width="36" height="36" viewBox="0 0 36 36" fill="none">
          <defs><linearGradient id="lg" x1="3" y1="4" x2="28" y2="32" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#0066FF"/><stop offset="100%" stop-color="#00A3FF"/></linearGradient></defs>
          <path d="M28 8C24.5 5.5 20 4 15 4C8.4 4 3 9.4 3 18s5.4 14 12 14c5 0 9.5-1.5 13-4" stroke="url(#lg)" stroke-width="3.5" stroke-linecap="round" fill="none"/>
          <circle cx="28" cy="8" r="2.5" fill="#00A3FF"/>
          <circle cx="28" cy="28" r="2.5" fill="#00A3FF"/>
          <line x1="28" y1="8" x2="33" y2="8" stroke="#00A3FF" stroke-width="1.5"/>
          <circle cx="33" cy="8" r="1.5" fill="#00A3FF"/>
          <line x1="28" y1="28" x2="33" y2="28" stroke="#00A3FF" stroke-width="1.5"/>
          <circle cx="33" cy="28" r="1.5" fill="#00A3FF"/>
          <rect x="11" y="11" width="11" height="14" rx="1.5" fill="rgba(0,102,255,0.08)" stroke="rgba(0,102,255,0.25)" stroke-width="0.75"/>
          <line x1="13" y1="15" x2="20" y2="15" stroke="rgba(0,102,255,0.4)" stroke-width="0.75"/>
          <line x1="13" y1="18" x2="20" y2="18" stroke="rgba(0,102,255,0.4)" stroke-width="0.75"/>
          <line x1="13" y1="21" x2="18" y2="21" stroke="#00A3FF" stroke-width="1"/>
        </svg></span><span class="logo-name">${COMPANY.brand}</span></div>
    <div class="company-detail">${COMPANY.name}<br>GSTIN: ${COMPANY.gstin}<br>${COMPANY.address}<br>${COMPANY.email} · ${COMPANY.website}</div>
  </div>
  <div style="text-align:right">
    <div class="invoice-title">TAX INVOICE</div>
    <div class="invoice-sub">${invoiceNo} &nbsp;·&nbsp; ${dateStr}</div>
    <span class="badge">✓ PAID</span>
  </div>
</div>
<div class="plan-box">
  <div>
    <div class="plan-tag">Current Plan</div>
    <div class="plan-name">${planLabel} Plan${inv.addon?" + Industry Pack":""}</div>
    <div class="plan-period">${period}</div>
  </div>
  <div>
    <div class="plan-total">₹${total.toLocaleString("en-IN")}</div>
    <div class="plan-total-label">Total paid · incl. GST</div>
  </div>
</div>
<div class="section-label">Charge Breakdown</div>
<table>
  <thead><tr><th>Description</th><th>Period</th><th>Amount</th></tr></thead>
  <tbody>
    <tr><td><strong>${planLabel} Plan</strong></td><td>${period}</td><td>₹${base.toLocaleString("en-IN")}</td></tr>
    ${addon>0?`<tr><td><strong>Industry Pack Add-on</strong></td><td>${period}</td><td>₹${addon.toLocaleString("en-IN")}</td></tr>`:""}
    ${credit>0?`<tr class="credit-row"><td><strong>Pro-rata Credit</strong> <span style="font-size:11px;font-weight:400">(Previous plan unused days)</span></td><td>—</td><td>−₹${credit.toLocaleString("en-IN")}</td></tr>`:""}
    <tr class="muted-row"><td>CGST @ 9%</td><td></td><td>₹${cgst.toLocaleString("en-IN")}</td></tr>
    <tr class="muted-row"><td>SGST @ 9%</td><td></td><td>₹${sgst.toLocaleString("en-IN")}</td></tr>
  </tbody>
</table>
<table><tbody><tr class="total-row"><td>Total Amount Paid</td><td></td><td>₹${total.toLocaleString("en-IN")}</td></tr></tbody></table>
<div class="grid2">
  <div class="info-box"><div class="info-title">Billed To</div><div class="info-val">${summary?.org_name||"Organisation"}<br>${summary?.email||""}</div></div>
  <div class="info-box"><div class="info-title">Payment Info</div><div class="info-val">Provider: Razorpay<br>Method: Card / UPI / Netbanking<br>Status: <strong style="color:#16A34A">Paid</strong></div></div>
</div>
<div class="footer">
  <div class="footer-left"><strong>${COMPANY.brand}</strong> by ${COMPANY.name}<br>GSTIN: ${COMPANY.gstin} · ${COMPANY.email}</div>
  <div class="footer-right">Computer-generated invoice<br>No signature required</div>
</div>
</div></body></html>`;
    const blob=new Blob([html],{type:"text/html"});
    const url=URL.createObjectURL(blob);
    const w=window.open(url,"_blank");
    if(w) setTimeout(()=>w.print(),600);
  };

  const currentPlan     = summary?.plan || "free";
  const currentPlanObj  = PLANS.find(p=>p.id===currentPlan);
  const monthlyBase     = (currentPlanObj?.base && currentPlanObj.base > 0) ? currentPlanObj.base : 0;
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
            {currentPlan === "enterprise" ? (
              <div style={{padding:"16px 24px",background:C.primaryLight,borderRadius:10,
                border:`1px solid ${C.primary}`,textAlign:"center"}}>
                <div style={{fontSize:22,fontWeight:900,color:C.primary}}>Custom Pricing</div>
                <div style={{fontSize:12,color:C.primary,marginTop:4,opacity:0.7}}>
                  Contact sales@claustor.com
                </div>
              </div>
            ) : monthlySubtotal > 0 ? (
              <div style={{textAlign:"right",padding:"16px 20px",
                background:C.bg,borderRadius:10,border:`1px solid ${C.border}`}}>
                <div style={{fontSize:11,color:C.muted,marginBottom:8,fontWeight:600,
                  textTransform:"uppercase",letterSpacing:"0.06em"}}>
                  {summary?.billing_period === "6months" ? "6-Month Rate" :
                   summary?.billing_period === "12months" ? "12-Month Rate" :
                   "Monthly Rate"}
                </div>
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
                  <div style={{fontSize:10,color:C.muted}}>incl. GST · per month</div>
                  {summary?.billing_period && summary.billing_period !== "monthly" && (() => {
                    const months = summary.billing_period === "6months" ? 5 : 10;
                    const freeMo = summary.billing_period === "6months" ? 1 : 2;
                    const paid   = monthlyTotal * months;
                    return (
                      <div style={{marginTop:8,padding:"6px 10px",borderRadius:6,
                        background:"#EFF6FF",fontSize:11,color:C.primary,fontWeight:600}}>
                        Paid ₹{paid.toLocaleString()} for {months+freeMo} months
                        ({freeMo} month{freeMo>1?"s":""} free)
                      </div>
                    );
                  })()}
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
            <div>₹{(()=>{const b=inv.base_amount||0; return b>100000?Math.round(b/100):b;})(). toLocaleString()}</div>
            <div>{inv.addon_amount>0?`₹${inv.addon_amount.toLocaleString()}`:<span style={{color:C.muted}}>—</span>}</div>
            <div style={{fontWeight:700,color:C.heading}}>
              ₹{(()=>{const t=inv.total_amount||inv.amount||0; return t>100000?Math.round(t/100):t;})(). toLocaleString()}
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
      {/* ── Addon + Period Modal ──────────────────────────────── */}
      {addonModal && (()=>{
        const plan = PLANS.find(p=>p.id===addonModal.planId);
        if (!plan) return null;
        const GST = 0.18;
        const baseMonthly = plan.base;
        const addonMonthly = plan.addon;
        const monthly = Math.round((baseMonthly + (addonSelected?addonMonthly:0)) * (1+GST));
        const periods: {key:"monthly"|"6months"|"12months"; label:string; months:number; free:number; badge:string}[] = [
          {key:"monthly",  label:"Monthly",   months:1,  free:0, badge:""},
          {key:"6months",  label:"6 Months",  months:5,  free:1, badge:"1 Month FREE"},
          {key:"12months", label:"12 Months", months:10, free:2, badge:"BEST VALUE"},
        ];
        // Refresh prorate when period or addon changes
        const [_pr, _setPr] = [proRate, setProRate];
        const refreshProrate = (newPeriod: string, newAddon: boolean) => {
          if (!addonModal || addonModal.planId !== "professional") return;
          const token = getToken();
          fetch(`${API}/api/v1/billing/razorpay/prorate?target_plan=professional&period=${newPeriod}&addon=${newAddon}`,{
            headers:{Authorization:`Bearer ${token}`}
          }).then(r=>r.ok?r.json():null).then(d=>{if(d)setProRate(d);}).catch(()=>{});
        };
        const sel = periods.find(p=>p.key===periodSelected)!;
        const total = monthly * sel.months;
        const saving = monthly * sel.free;

        return (
          <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.55)",
            display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000,
            padding:"16px"}}>
            <div style={{background:"white",borderRadius:16,padding:28,
              maxWidth:460,width:"100%",boxShadow:"0 20px 60px rgba(0,0,0,0.25)"}}>

              {/* Header */}
              <div style={{marginBottom:20}}>
                <h3 style={{fontSize:18,fontWeight:800,color:"#111827",marginBottom:4}}>
                  Upgrade to {plan.label}
                </h3>
                <p style={{fontSize:13,color:"#6B7280"}}>
                  Choose your billing period and optionally add the Industry Pack.
                </p>
              </div>

              {/* Addon toggle */}
              {plan.addon > 0 && (
                <div onClick={()=>{ setAddonSelected(!addonSelected); refreshProrate(periodSelected, !addonSelected); }}
                  style={{padding:"12px 16px",borderRadius:10,marginBottom:16,
                    background:addonSelected?"#EFF6FF":"#F8FAFC",
                    border:`2px solid ${addonSelected?"#0066FF":"#E5E7EB"}`,
                    cursor:"pointer",transition:"all 0.15s"}}>
                  <div style={{display:"flex",alignItems:"center",gap:10}}>
                    <div style={{width:20,height:20,borderRadius:5,flexShrink:0,
                      background:addonSelected?"#0066FF":"white",
                      border:`2px solid ${addonSelected?"#0066FF":"#D1D5DB"}`,
                      display:"flex",alignItems:"center",justifyContent:"center"}}>
                      {addonSelected&&<span style={{color:"white",fontSize:11,fontWeight:900}}>✓</span>}
                    </div>
                    <div style={{flex:1}}>
                      <div style={{fontSize:13,fontWeight:700,color:"#111827"}}>
                        Add Industry Pack
                      </div>
                      <div style={{fontSize:11,color:"#6B7280"}}>
                        8 industries · custom scoring · priority queue
                      </div>
                    </div>
                    <div style={{fontSize:13,fontWeight:700,color:"#F59E0B",flexShrink:0}}>
                      +₹{plan.addon.toLocaleString()}/mo
                    </div>
                  </div>
                </div>
              )}

              {/* Period selector */}
              <div style={{marginBottom:16}}>
                <div style={{fontSize:11,fontWeight:700,color:"#6B7280",
                  textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:8}}>
                  Billing Period
                </div>
                <div style={{display:"flex",flexDirection:"column",gap:8}}>
                  {periods.map(p=>{
                    const amt = monthly * p.months;
                    const save = monthly * p.free;
                    const isSelected = periodSelected===p.key;
                    return (
                      <div key={p.key} onClick={()=>{ setPeriodSelected(p.key); refreshProrate(p.key, addonSelected); }}
                        style={{padding:"12px 16px",borderRadius:10,
                          background:isSelected?"#EFF6FF":"#F8FAFC",
                          border:`2px solid ${isSelected?"#0066FF":"#E5E7EB"}`,
                          cursor:"pointer",transition:"all 0.15s",
                          display:"flex",alignItems:"center",justifyContent:"space-between"}}>
                        <div style={{display:"flex",alignItems:"center",gap:10}}>
                          <div style={{width:18,height:18,borderRadius:"50%",flexShrink:0,
                            background:isSelected?"#0066FF":"white",
                            border:`2px solid ${isSelected?"#0066FF":"#D1D5DB"}`,
                            display:"flex",alignItems:"center",justifyContent:"center"}}>
                            {isSelected&&<div style={{width:7,height:7,borderRadius:"50%",background:"white"}}/>}
                          </div>
                          <div>
                            <div style={{display:"flex",alignItems:"center",gap:6}}>
                              <span style={{fontSize:13,fontWeight:700,color:"#111827"}}>
                                {p.label}
                              </span>
                              {p.badge && (
                                <span style={{fontSize:10,fontWeight:700,padding:"2px 7px",
                                  borderRadius:20,
                                  background:p.key==="12months"?"#0066FF":"#F59E0B",
                                  color:"white"}}>
                                  {p.badge}
                                </span>
                              )}
                            </div>
                            {save>0 && (
                              <div style={{fontSize:11,color:"#22C55E",fontWeight:600}}>
                                Save ₹{save.toLocaleString()} ({p.free} month{p.free>1?"s":""} free)
                              </div>
                            )}
                          </div>
                        </div>
                        <div style={{textAlign:"right",flexShrink:0}}>
                          <div style={{fontSize:15,fontWeight:800,color:isSelected?"#0066FF":"#111827"}}>
                            ₹{amt.toLocaleString()}
                          </div>
                          {p.key!=="monthly" && (
                            <div style={{fontSize:10,color:"#6B7280"}}>
                              ₹{Math.round(amt/p.months).toLocaleString()}/mo
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Total summary */}
              <div style={{padding:"12px 16px",borderRadius:10,marginBottom:20,
                background:"#F0FDF4",border:"1px solid #BBF7D0"}}>
                {/* Pro-rata credit breakdown */}
                {proRate?.has_credit && (
                  <div style={{marginBottom:8,paddingBottom:8,borderBottom:"1px solid #BBF7D0"}}>
                    {proRate.free_upgrade ? (
                      <div style={{background:"#F0FDF4",border:"1px solid #22C55E30",
                        borderRadius:8,padding:"10px 12px",marginBottom:8}}>
                        <div style={{fontSize:12,fontWeight:700,color:"#16A34A",marginBottom:3}}>
                          🎉 Free Upgrade!
                        </div>
                        <div style={{fontSize:11,color:"#374151"}}>
                          Your starter credit (₹{proRate.credit_applied.toLocaleString()}) covers the full Professional plan.
                          {proRate.extra_days > 0 && ` Plus ${proRate.extra_days} bonus days added.`}
                        </div>
                      </div>
                    ) : (
                      <>
                        <div style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:3}}>
                          <span style={{color:"#6B7280"}}>New plan price</span>
                          <span style={{color:"#111827"}}>₹{proRate.new_plan_price.toLocaleString()}</span>
                        </div>
                        <div style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:3}}>
                          <span style={{color:"#16A34A"}}>Starter credit ({proRate.remaining_days} days)</span>
                          <span style={{color:"#16A34A",fontWeight:700}}>-₹{proRate.credit_applied.toLocaleString()}</span>
                        </div>
                        <div style={{display:"flex",justifyContent:"space-between",fontSize:12}}>
                          <span style={{color:"#6B7280"}}>GST (18%)</span>
                          <span style={{color:"#111827"}}>₹{proRate.gst.toLocaleString()}</span>
                        </div>
                      </>
                    )}
                  </div>
                )}
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <div>
                    <div style={{fontSize:12,color:"#6B7280"}}>
                      {plan.label} {addonSelected?"+ Industry Pack":""} · {sel.label}
                    </div>
                    {saving>0&&!proRate?.has_credit&&(
                      <div style={{fontSize:11,color:"#22C55E",fontWeight:600}}>
                        You save ₹{saving.toLocaleString()} vs monthly
                      </div>
                    )}
                  </div>
                  <div style={{textAlign:"right"}}>
                    <div style={{fontSize:20,fontWeight:900,color:"#111827"}}>
                      ₹{proRate?.has_credit ? proRate.total_to_pay.toLocaleString() : total.toLocaleString()}
                    </div>
                    <div style={{fontSize:10,color:"#6B7280"}}>incl. 18% GST</div>
                  </div>
                </div>
              </div>

              {/* Buttons */}
              <div style={{display:"flex",gap:10}}>
                <button onClick={()=>setAddonModal(null)}
                  style={{flex:1,padding:"11px",border:"1px solid #E5E7EB",
                    borderRadius:10,background:"white",cursor:"pointer",
                    fontSize:13,color:"#6B7280",fontWeight:600}}>
                  Cancel
                </button>
                <button onClick={()=>{
                  const {planId,action}=addonModal;
                  setAddonModal(null);
                  handlePlanAction(planId, action, addonSelected, periodSelected, proRate);
                }}
                  style={{flex:2,padding:"11px",border:"none",borderRadius:10,
                    background:"#0066FF",cursor:"pointer",
                    fontSize:13,color:"white",fontWeight:700}}>
                  {proRate?.free_upgrade ? "Upgrade Now (Free) →" : `Pay ₹${proRate?.has_credit ? proRate.total_to_pay.toLocaleString() : total.toLocaleString()} →`}
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* ── Enterprise Contact Modal ──────────────────────────── */}
      {enterpriseModal && (
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.55)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000,padding:16}}>
          <div style={{background:"white",borderRadius:16,padding:28,maxWidth:500,width:"100%",maxHeight:"90vh",overflowY:"auto",boxShadow:"0 20px 60px rgba(0,0,0,0.25)"}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:20}}>
              <div>
                <div style={{fontSize:18,fontWeight:800,color:"#111827",marginBottom:4}}>Enterprise Plan</div>
                <div style={{fontSize:13,color:"#6B7280"}}>Unlimited contracts · Custom AI · Dedicated support</div>
              </div>
              <button onClick={()=>{setEnterpriseModal(false);setEnterpriseMsg("");}} style={{background:"none",border:"none",cursor:"pointer",fontSize:20,color:"#9CA3AF"}}>✕</button>
            </div>
            <div style={{background:"linear-gradient(135deg,#0A1128,#0066FF)",borderRadius:10,padding:"14px 16px",marginBottom:20}}>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6}}>
                {["Unlimited contracts","Custom risk scoring","Dedicated account manager","SLA guarantee","On-premise option","Custom integrations"].map(f=>(
                  <div key={f} style={{fontSize:11,color:"rgba(255,255,255,0.85)",display:"flex",alignItems:"center",gap:6}}><span style={{color:"#22C55E"}}>✓</span>{f}</div>
                ))}
              </div>
            </div>
            {enterpriseMsg && !enterpriseMsg.startsWith("❌") ? (
              <div style={{textAlign:"center",padding:"32px 0"}}>
                <div style={{fontSize:32,marginBottom:12}}>✅</div>
                <div style={{fontSize:15,fontWeight:700,color:"#111827",marginBottom:8}}>Request Sent!</div>
                <div style={{fontSize:13,color:"#6B7280",marginBottom:16}}>{enterpriseMsg}</div>
                <div style={{fontSize:12,color:"#6B7280"}}>Direct: <a href="mailto:sales@claustor.com" style={{color:C.primary,fontWeight:600}}>sales@claustor.com</a></div>
                <button onClick={()=>{setEnterpriseModal(false);setEnterpriseMsg("");}} style={{marginTop:16,padding:"10px 24px",background:C.primary,color:"white",border:"none",borderRadius:8,cursor:"pointer",fontSize:13,fontWeight:700}}>Close</button>
              </div>
            ) : (
              <>
                {enterpriseMsg && <div style={{color:"#DC2626",fontSize:12,marginBottom:12}}>{enterpriseMsg}</div>}
                {[{k:"business_name",l:"Business Name *",t:"text",p:"Acme Corp Pvt. Ltd."},
                  {k:"contact_name",l:"Your Name *",t:"text",p:"Rajesh Kumar"},
                  {k:"business_email",l:"Business Email *",t:"email",p:"rajesh@acme.com"},
                  {k:"mobile",l:"Mobile Number",t:"tel",p:"+91 98765 43210"}].map(f=>(
                  <div key={f.k} style={{marginBottom:12}}>
                    <label style={{fontSize:11,fontWeight:700,color:"#374151",display:"block",marginBottom:4}}>{f.l}</label>
                    <input type={f.t} placeholder={f.p} value={(enterpriseForm as any)[f.k]}
                      onChange={e=>setEnterpriseForm(p=>({...p,[f.k]:e.target.value}))}
                      style={{width:"100%",padding:"9px 12px",border:"1px solid #E5E7EB",borderRadius:8,fontSize:13,outline:"none",fontFamily:"inherit",boxSizing:"border-box"}}/>
                  </div>
                ))}
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:12}}>
                  <div>
                    <label style={{fontSize:11,fontWeight:700,color:"#374151",display:"block",marginBottom:4}}>Industry *</label>
                    <select value={enterpriseForm.industry} onChange={e=>setEnterpriseForm(p=>({...p,industry:e.target.value}))} style={{width:"100%",padding:"9px 12px",border:"1px solid #E5E7EB",borderRadius:8,fontSize:13,background:"white",boxSizing:"border-box"}}>
                      <option value="">Select...</option>
                      {["Legal","Finance & Banking","Healthcare","Technology","Manufacturing","Real Estate","Education","Other"].map(i=><option key={i}>{i}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{fontSize:11,fontWeight:700,color:"#374151",display:"block",marginBottom:4}}>Company Size *</label>
                    <select value={enterpriseForm.company_size} onChange={e=>setEnterpriseForm(p=>({...p,company_size:e.target.value}))} style={{width:"100%",padding:"9px 12px",border:"1px solid #E5E7EB",borderRadius:8,fontSize:13,background:"white",boxSizing:"border-box"}}>
                      <option value="">Select...</option>
                      {["1–10","11–50","51–200","201–500","500+"].map(s=><option key={s}>{s} employees</option>)}
                    </select>
                  </div>
                </div>
                <div style={{marginBottom:12}}>
                  <label style={{fontSize:11,fontWeight:700,color:"#374151",display:"block",marginBottom:4}}>Contracts / Month</label>
                  <select value={enterpriseForm.contracts_per_month} onChange={e=>setEnterpriseForm(p=>({...p,contracts_per_month:e.target.value}))} style={{width:"100%",padding:"9px 12px",border:"1px solid #E5E7EB",borderRadius:8,fontSize:13,background:"white",boxSizing:"border-box"}}>
                    <option value="">Select...</option>
                    {["< 100","100–500","500–1,000","1,000–5,000","5,000+"].map(s=><option key={s}>{s}</option>)}
                  </select>
                </div>
                <div style={{marginBottom:20}}>
                  <label style={{fontSize:11,fontWeight:700,color:"#374151",display:"block",marginBottom:4}}>Message / Requirements</label>
                  <textarea placeholder="Tell us about your use case..." value={enterpriseForm.message} onChange={e=>setEnterpriseForm(p=>({...p,message:e.target.value}))} rows={3} style={{width:"100%",padding:"9px 12px",border:"1px solid #E5E7EB",borderRadius:8,fontSize:13,fontFamily:"inherit",resize:"vertical",outline:"none",boxSizing:"border-box"}}/>
                </div>
                <div style={{display:"flex",gap:10}}>
                  <button onClick={()=>setEnterpriseModal(false)} style={{flex:1,padding:"11px",border:"1px solid #E5E7EB",borderRadius:10,background:"white",cursor:"pointer",fontSize:13,color:"#6B7280",fontWeight:600}}>Cancel</button>
                  <button disabled={enterpriseSending} onClick={async()=>{
                    if(!enterpriseForm.business_name||!enterpriseForm.contact_name||!enterpriseForm.business_email||!enterpriseForm.industry||!enterpriseForm.company_size){setEnterpriseMsg("❌ Please fill all required fields.");return;}
                    setEnterpriseSending(true);
                    try{const r=await fetch(`${API}/api/v1/billing/enterprise/contact`,{method:"POST",headers:{Authorization:`Bearer ${getToken()}`,"Content-Type":"application/json"},body:JSON.stringify(enterpriseForm)});const d=await r.json();setEnterpriseMsg(d.message||"Sent!");}
                    catch(e){setEnterpriseMsg("❌ Failed. Email sales@claustor.com");}
                    finally{setEnterpriseSending(false);}
                  }} style={{flex:2,padding:"11px",border:"none",borderRadius:10,background:enterpriseSending?"#9CA3AF":C.primary,cursor:enterpriseSending?"not-allowed":"pointer",fontSize:13,color:"white",fontWeight:700}}>
                    {enterpriseSending?"Sending...":"Send Request →"}
                  </button>
                </div>
                <div style={{textAlign:"center",marginTop:14,fontSize:11,color:"#9CA3AF"}}>Direct: <a href="mailto:sales@claustor.com" style={{color:C.primary,fontWeight:600}}>sales@claustor.com</a></div>
              </>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
