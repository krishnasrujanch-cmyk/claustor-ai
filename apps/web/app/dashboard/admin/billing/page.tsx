"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { billing as billingAPI, getToken } from "@/lib/api";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  success:"#22C55E", warning:"#F59E0B", error:"#EF4444",
};

const ALL_INDUSTRIES = [
  { id:"general",      icon:"📄", label:"General / Other",           description:"Standard analysis",              minPlan:null,           requiresAddon:[] },
  { id:"it_saas",      icon:"💻", label:"IT / SaaS",                 description:"SLA, IP rights, vendor lock-in", minPlan:"starter",      requiresAddon:["starter","professional","enterprise"] },
  { id:"manufacturing",icon:"🏭", label:"Manufacturing",             description:"Quality, volume, force majeure",  minPlan:"starter",      requiresAddon:["starter","professional","enterprise"] },
  { id:"hr_employment",icon:"👥", label:"HR / Employment",           description:"Non-compete, IP, termination",   minPlan:"professional", requiresAddon:["professional","enterprise"] },
  { id:"legal",        icon:"⚖️", label:"Legal / Professional",      description:"Retainer, conflicts, privilege", minPlan:"professional", requiresAddon:["professional","enterprise"] },
  { id:"real_estate",  icon:"🏢", label:"Real Estate / Lease",       description:"Rent escalation, exit clauses",  minPlan:"professional", requiresAddon:["professional","enterprise"] },
  { id:"pharma",       icon:"💊", label:"Pharma / Life Sciences",    description:"FDA, IP exclusivity, clinical",  minPlan:"professional", requiresAddon:["professional","enterprise"] },
  { id:"banking",      icon:"🏦", label:"Banking / Finance",         description:"RBI/SEBI, data residency, AML",  minPlan:"professional", requiresAddon:["professional","enterprise"] },
];

const PLANS = [
  {
    id: "free", label: "Free", base: 0, addon: 0,
    tagline: "Get started",
    features: ["5 contracts", "100 AI queries/month", "1 user", "General industry only"],
    addonFeatures: [],
  },
  {
    id: "starter", label: "Starter", base: 3999, addon: 1000,
    tagline: "For small teams",
    features: ["100 contracts", "5,000 AI queries/month", "5 users", "Email alerts", "General industry only"],
    addonFeatures: ["IT/SaaS industry scoring", "Manufacturing scoring", "Industry clause priorities"],
    addonLabel: "Industry Pack (+₹1,000/mo)",
  },
  {
    id: "professional", label: "Professional", base: 16499, addon: 2500,
    tagline: "For growing businesses", popular: true,
    features: ["1,000 contracts", "50,000 AI queries/month", "25 users", "Webhooks", "Bulk import", "Review workflow", "All 8 industries base"],
    addonFeatures: ["Custom clause weights", "Priority queue processing", "Dedicated industry playbooks", "All 8 industries unlocked"],
    addonLabel: "Pro Industry Add-on (+₹2,500/mo)",
  },
  {
    id: "enterprise", label: "Enterprise", base: 0, addon: 0,
    tagline: "For large organisations",
    features: ["Unlimited contracts", "Unlimited queries", "Unlimited users", "SSO", "SLA guarantee", "All industries + custom weights", "White-label"],
    addonFeatures: [],
  },
];

export default function BillingPage() {
  const [summary, setSummary]     = useState<any>(null);
  const [invoices, setInvoices]   = useState<any[]>([]);
  const [orgInd, setOrgInd]       = useState<any>(null);
  const [addonEnabled, setAddonEnabled] = useState(false);
  const [loading, setLoading]     = useState(true);
  const [upgrading, setUpgrading] = useState<string|null>(null);
  const [togglingAddon, setTogglingAddon] = useState(false);
  const [msg, setMsg]             = useState("");

  const load = async () => {
    const token = getToken();
    const h = { Authorization: `Bearer ${token}` };
    try {
      const [s, inv, ind] = await Promise.all([
        billingAPI.summary(),
        billingAPI.invoices(),
        fetch(`${API}/api/v1/industries/org`, { headers: h }).then(r => r.json()),
      ]);
      setSummary(s);
      setInvoices((inv as any).invoices || []);
      setOrgInd(ind);
      setAddonEnabled(ind.addon_enabled || false);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const upgrade = async (planId: string) => {
    if (planId === "enterprise") { window.open("mailto:sales@claustor.com"); return; }
    setUpgrading(planId); setMsg("");
    const token = getToken();
    try {
      const r = await fetch(`${API}/api/v1/billing/subscribe`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ plan: planId }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail);
      setMsg(`✅ Plan updated to ${planId}!`);
      await load();
    } catch(e: any) { setMsg(`❌ ${e.message}`); }
    finally { setUpgrading(null); }
  };

  const toggleAddon = async (enabled: boolean) => {
    setTogglingAddon(true); setMsg("");
    const token = getToken();
    try {
      const r = await fetch(`${API}/api/v1/industries/org/addon`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
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

  const currentPlan = summary?.plan || "free";
  const currentPlanObj = PLANS.find(p => p.id === currentPlan);
  const monthlyBase  = currentPlanObj?.base || 0;
  const monthlyAddon = addonEnabled ? (currentPlanObj?.addon || 0) : 0;
  const monthlyTotal = monthlyBase + monthlyAddon;
  const PLAN_ORDER   = ["free","starter","professional","enterprise"];
  const currentIdx   = PLAN_ORDER.indexOf(currentPlan);

  if (loading) return <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading...</div>;

  return (
    <div style={{padding:"32px 36px", maxWidth:1100}}>
      <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Billing</h1>
      <p style={{fontSize:14,color:C.muted,marginBottom:24}}>Manage your plan and industry add-ons</p>

      {msg && (
        <div style={{padding:"12px 16px",borderRadius:8,marginBottom:20,
          background:msg.startsWith("✅")?"#F0FDF4":"#FEF2F2",
          color:msg.startsWith("✅")?C.success:C.error,fontSize:14}}>
          {msg}
        </div>
      )}

      {/* Current Plan Summary */}
      {summary && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:12,padding:24,marginBottom:24}}>
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:20}}>
            <div>
              <div style={{fontSize:12,color:C.muted,marginBottom:4}}>Current plan</div>
              <div style={{fontSize:22,fontWeight:800,color:C.primary,
                textTransform:"capitalize",marginBottom:4}}>{currentPlan}</div>
              {addonEnabled && currentPlanObj?.addonLabel && (
                <div style={{fontSize:12,color:C.warning,display:"flex",alignItems:"center",gap:6}}>
                  <span>✓</span> {currentPlanObj.addonLabel} active
                </div>
              )}
            </div>
            <div style={{textAlign:"right"}}>
              <div style={{fontSize:12,color:C.muted,marginBottom:4}}>Monthly total</div>
              {monthlyTotal > 0 ? (
                <>
                  <div style={{fontSize:22,fontWeight:800,color:C.heading}}>
                    ₹{monthlyTotal.toLocaleString()}
                    <span style={{fontSize:12,color:C.muted,fontWeight:400}}>/mo</span>
                  </div>
                  <div style={{fontSize:11,color:C.muted}}>
                    +18% GST = ₹{Math.round(monthlyTotal*1.18).toLocaleString()}
                  </div>
                  {monthlyAddon > 0 && (
                    <div style={{fontSize:11,color:C.warning,marginTop:2}}>
                      Base ₹{monthlyBase.toLocaleString()} + Add-on ₹{monthlyAddon.toLocaleString()}
                    </div>
                  )}
                </>
              ) : (
                <div style={{fontSize:18,fontWeight:800,color:C.success}}>Free</div>
              )}
            </div>
          </div>

          {/* Usage bars */}
          {summary.usage && Object.entries(summary.usage).map(([k,v]:any) => (
            <div key={k} style={{marginBottom:12}}>
              <div style={{display:"flex",justifyContent:"space-between",fontSize:13,marginBottom:4}}>
                <span style={{color:C.body,textTransform:"capitalize"}}>{k.replace(/_/g," ")}</span>
                <span style={{color:v.pct>80?C.error:C.muted}}>{v.used}/{v.limit}</span>
              </div>
              <div style={{height:6,background:C.border,borderRadius:3,overflow:"hidden"}}>
                <div style={{height:"100%",width:`${Math.min(v.pct||0,100)}%`,borderRadius:3,
                  background:v.pct>90?C.error:v.pct>70?C.warning:C.primary}}/>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Industry Add-on Toggle (if plan supports it) */}
      {currentPlanObj?.addon > 0 && (
        <div style={{background:addonEnabled?C.primaryLight:C.surface,
          border:`2px solid ${addonEnabled?C.primary:C.border}`,
          borderRadius:12,padding:24,marginBottom:24}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
            <div style={{flex:1}}>
              <div style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:4}}>
                🏭 {currentPlanObj.addonLabel}
              </div>
              <div style={{fontSize:13,color:C.muted,marginBottom:12}}>
                {addonEnabled
                  ? `Active — ₹${currentPlanObj.addon.toLocaleString()}/month added to your bill`
                  : `Add ₹${currentPlanObj.addon.toLocaleString()}/month to unlock industry-specific features`
                }
              </div>
              <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
                {currentPlanObj.addonFeatures.map((f:string) => (
                  <span key={f} style={{fontSize:12,padding:"4px 10px",borderRadius:20,
                    background:addonEnabled?"#EEF0FF":"#F3F4F6",
                    color:addonEnabled?C.primary:C.muted}}>
                    {addonEnabled ? "✓" : "○"} {f}
                  </span>
                ))}
              </div>
            </div>

            {/* Toggle switch */}
            <div style={{marginLeft:24,display:"flex",flexDirection:"column",alignItems:"center",gap:8}}>
              <button
                onClick={() => toggleAddon(!addonEnabled)}
                disabled={togglingAddon}
                style={{
                  width:52, height:28, borderRadius:14, border:"none",
                  background: addonEnabled ? C.primary : C.border,
                  cursor: togglingAddon ? "not-allowed" : "pointer",
                  position:"relative", transition:"background 0.2s",
                }}>
                <div style={{
                  position:"absolute", top:3,
                  left: addonEnabled ? 27 : 3,
                  width:22, height:22, borderRadius:11,
                  background:"white", transition:"left 0.2s",
                  boxShadow:"0 1px 4px rgba(0,0,0,0.2)",
                }}/>
              </button>
              <span style={{fontSize:11,fontWeight:600,
                color:addonEnabled?C.primary:C.muted}}>
                {togglingAddon ? "..." : addonEnabled ? "ON" : "OFF"}
              </span>
            </div>
          </div>

          {addonEnabled && (
            <div style={{marginTop:16,padding:"12px 16px",background:"white",
              borderRadius:8,border:`1px solid ${C.primary}30`}}>
              <div style={{fontSize:12,fontWeight:600,color:C.body,marginBottom:6}}>
                Active industries:
              </div>
              <div style={{display:"flex",flexWrap:"wrap",gap:6}}>
                {(orgInd?.active_industries || []).map((ind:string) => (
                  <span key={ind} style={{fontSize:11,padding:"3px 10px",
                    borderRadius:20,background:C.primaryLight,color:C.primary,fontWeight:600}}>
                    {ind.replace(/_/g," ")}
                  </span>
                ))}
              </div>
              <div style={{marginTop:10,fontSize:12,color:C.muted}}>
                Configure industry in{" "}
                <Link href="/dashboard/settings" style={{color:C.primary,fontWeight:600}}>
                  Settings →
                </Link>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Industry Access Preview */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,
        borderRadius:12,padding:24,marginBottom:24}}>
        <div style={{display:"flex",justifyContent:"space-between",
          alignItems:"center",marginBottom:16}}>
          <h2 style={{fontSize:16,fontWeight:700,color:C.heading,margin:0}}>
            Industry Risk Scoring
          </h2>
          {currentPlan !== "enterprise" && (
            <span style={{fontSize:12,color:C.muted}}>
              Upgrade to unlock more industries
            </span>
          )}
        </div>
        <div style={{display:"grid",
          gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))",gap:12}}>
          {ALL_INDUSTRIES.map((ind:any) => {
            const isActive = (orgInd?.active_industries || ["general"]).includes(ind.id);
            const needsAddon = !isActive && ind.requiresAddon?.includes(currentPlan);
            const needsUpgrade = !isActive && !ind.requiresAddon?.includes(currentPlan);
            return (
              <div key={ind.id} style={{
                padding:"14px 16px",borderRadius:10,
                border:`1px solid ${isActive?C.primary:C.border}`,
                background: isActive ? C.primaryLight : "#FAFBFC",
                opacity: isActive ? 1 : 0.7,
                position:"relative",
              }}>
                <div style={{fontSize:18,marginBottom:4}}>{ind.icon}</div>
                <div style={{fontSize:13,fontWeight:700,
                  color:isActive?C.heading:C.muted,marginBottom:2}}>
                  {ind.label}
                </div>
                <div style={{fontSize:11,color:C.muted,marginBottom:8}}>
                  {ind.description}
                </div>
                {isActive ? (
                  <span style={{fontSize:11,fontWeight:700,color:C.primary,
                    background:C.primaryLight,padding:"2px 8px",borderRadius:20}}>
                    ✓ Active
                  </span>
                ) : needsAddon ? (
                  <button
                    onClick={() => toggleAddon(true)}
                    style={{fontSize:11,fontWeight:700,color:"white",
                      background:C.warning,padding:"3px 10px",borderRadius:20,
                      border:"none",cursor:"pointer",width:"100%"}}>
                    Enable Add-on →
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      const nextPlan = ind.minPlan || "professional";
                      if(confirm(`Upgrade to ${nextPlan} to unlock ${ind.label}?`)) {
                        upgrade(nextPlan);
                      }
                    }}
                    style={{fontSize:11,fontWeight:700,color:"white",
                      background:"#9CA3AF",padding:"3px 10px",borderRadius:20,
                      border:"none",cursor:"pointer",width:"100%"}}>
                    🔒 Upgrade to unlock
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Plan Cards */}
      <h2 style={{fontSize:17,fontWeight:700,color:C.heading,marginBottom:16}}>Available Plans</h2>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:16,marginBottom:32}}>
        {PLANS.map(plan => {
          const isCurrent = plan.id === currentPlan;
          const isUpgrade = PLAN_ORDER.indexOf(plan.id) > currentIdx;

          return (
            <div key={plan.id} style={{
              background: isCurrent ? C.primaryLight : C.surface,
              border:`2px solid ${isCurrent?C.primary:plan.popular?"#5B4BFF44":C.border}`,
              borderRadius:12, padding:20, position:"relative",
              display:"flex", flexDirection:"column",
            }}>
              {plan.popular && !isCurrent && (
                <div style={{position:"absolute",top:-10,left:"50%",
                  transform:"translateX(-50%)",background:C.primary,color:"white",
                  fontSize:10,fontWeight:700,padding:"2px 12px",borderRadius:20,
                  whiteSpace:"nowrap"}}>POPULAR</div>
              )}
              {isCurrent && (
                <div style={{position:"absolute",top:10,right:10,background:C.primary,
                  color:"white",fontSize:10,fontWeight:700,padding:"2px 8px",borderRadius:20}}>
                  Current
                </div>
              )}

              <div style={{fontSize:15,fontWeight:800,color:C.heading,marginBottom:2,
                textTransform:"capitalize"}}>{plan.label}</div>
              <div style={{fontSize:11,color:C.muted,marginBottom:12}}>{plan.tagline}</div>

              {/* Pricing */}
              <div style={{marginBottom:12}}>
                {plan.id === "enterprise" ? (
                  <div style={{fontSize:18,fontWeight:800,color:C.heading}}>Custom</div>
                ) : plan.base === 0 ? (
                  <div style={{fontSize:18,fontWeight:800,color:C.success}}>Free</div>
                ) : (
                  <div>
                    <div style={{fontSize:11,color:C.muted}}>from</div>
                    <span style={{fontSize:18,fontWeight:800,color:C.heading}}>
                      ₹{plan.base.toLocaleString()}
                    </span>
                    <span style={{fontSize:11,color:C.muted}}>/mo</span>
                    {plan.addon > 0 && (
                      <div style={{fontSize:11,color:C.warning,marginTop:2}}>
                        + ₹{plan.addon.toLocaleString()} add-on available
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Features */}
              <div style={{flex:1,marginBottom:16}}>
                {plan.features.map(f => (
                  <div key={f} style={{fontSize:11,color:C.body,padding:"2px 0",
                    display:"flex",gap:4}}>
                    <span style={{color:C.success,flexShrink:0}}>✓</span>
                    <span>{f}</span>
                  </div>
                ))}
                {plan.addonFeatures.length > 0 && (
                  <>
                    <div style={{fontSize:10,fontWeight:700,color:C.warning,
                      marginTop:8,marginBottom:4}}>+ WITH ADD-ON:</div>
                    {plan.addonFeatures.map(f => (
                      <div key={f} style={{fontSize:11,color:C.warning,padding:"2px 0",
                        display:"flex",gap:4}}>
                        <span style={{flexShrink:0}}>★</span>
                        <span>{f}</span>
                      </div>
                    ))}
                  </>
                )}
              </div>

              {!isCurrent && (
                <button
                  onClick={() => {
                    if (plan.id === "free") window.open("mailto:support@claustor.com");
                    else if (plan.id === "enterprise") window.open("mailto:sales@claustor.com");
                    else upgrade(plan.id);
                  }}
                  disabled={upgrading===plan.id}
                  style={{padding:"8px 0",width:"100%",border:"none",borderRadius:8,
                    fontSize:12,fontWeight:600,cursor:upgrading===plan.id?"not-allowed":"pointer",
                    background:isUpgrade?C.primary:"#F3F4F6",
                    color:isUpgrade?"white":C.muted}}>
                  {upgrading===plan.id ? "Processing..." :
                   plan.id==="enterprise" ? "Contact sales" :
                   plan.id==="free" ? "Contact support" :
                   isUpgrade ? "Upgrade →" : "Downgrade"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Invoice History */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24}}>
        <h2 style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:16}}>Invoice history</h2>
        {invoices.length === 0
          ? <p style={{color:C.muted,fontSize:14}}>No invoices yet.</p>
          : (
            <table style={{width:"100%",borderCollapse:"collapse"}}>
              <thead>
                <tr>{["Period","Base Plan","Add-on","Total","Status"].map(h=>(
                  <th key={h} style={{padding:"8px 0",textAlign:"left",fontSize:12,
                    fontWeight:600,color:C.muted,borderBottom:`1px solid ${C.border}`}}>{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {invoices.map((inv:any)=>(
                  <tr key={inv.id} style={{borderBottom:`1px solid ${C.border}`}}>
                    <td style={{padding:"12px 0",fontSize:13,color:C.body}}>
                      {new Date(inv.period_start).toLocaleDateString("en-IN",
                        {month:"short",year:"numeric"})}
                    </td>
                    <td style={{padding:"12px 0",fontSize:13,color:C.body}}>
                      ₹{(inv.base_amount||inv.amount).toLocaleString()}
                    </td>
                    <td style={{padding:"12px 0",fontSize:13,color:C.warning}}>
                      {inv.industry_amount?`+₹${inv.industry_amount.toLocaleString()}`:"—"}
                    </td>
                    <td style={{padding:"12px 0",fontSize:14,fontWeight:600,color:C.heading}}>
                      ₹{inv.amount.toLocaleString()}
                    </td>
                    <td style={{padding:"12px 0"}}>
                      <span style={{fontSize:11,fontWeight:600,padding:"2px 8px",
                        borderRadius:20,background:"#F0FDF4",color:"#16A34A"}}>
                        {inv.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        }
      </div>
    </div>
  );
}
