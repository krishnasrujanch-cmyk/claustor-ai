"use client";
import { useEffect, useState } from "react";
import { billing as billingAPI, getToken } from "@/lib/api";
import { C } from "@/lib/design-tokens";

const API = "http://localhost:8000";
const PLANS = [
  {
    id: "free", label: "Free", price: 0,
    features: ["5 contracts", "100 AI queries/month", "General industry only", "1 user", "Basic risk scoring"],
    industries: ["General only"],
  },
  {
    id: "starter", label: "Starter", price: 4999,
    features: ["100 contracts", "5,000 AI queries/month", "3 industries", "5 users", "Email alerts", "Obligations tracking"],
    industries: ["General", "IT/SaaS", "Manufacturing", "HR/Employment"],
  },
  {
    id: "professional", label: "Professional", price: 14999, popular: true,
    features: ["1,000 contracts", "50,000 AI queries/month", "All 8 industries", "25 users", "Webhooks", "Bulk import", "Review workflow", "Playbooks"],
    industries: ["All 8 industries"],
  },
  {
    id: "enterprise", label: "Enterprise", price: 0,
    features: ["Unlimited contracts", "Unlimited queries", "All industries + custom weights", "Unlimited users", "SSO", "SLA guarantee", "Dedicated workers"],
    industries: ["All industries + custom weights"],
  },
];

const PLAN_ORDER = ["free","starter","professional","enterprise"];

export default function BillingPage() {
  const [summary, setSummary]   = useState<any>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [orgInd, setOrgInd]     = useState<any>(null);
  const [loading, setLoading]   = useState(true);
  const [upgrading, setUpgrading] = useState<string|null>(null);
  const [msg, setMsg]             = useState("");

  const load = async () => {
    const token = getToken();
    const h = { Authorization: `Bearer ${token}` };
    const [s, inv, ind] = await Promise.all([
      billingAPI.summary(),
      billingAPI.invoices(),
      fetch(`${API}/api/v1/industries/org`, { headers: h }).then(r => r.json()),
    ]);
    setSummary(s); setInvoices((inv as any).invoices || []); setOrgInd(ind);
    setLoading(false);
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

  const currentPlan    = summary?.plan || "free";
  const currentPlanIdx = PLAN_ORDER.indexOf(currentPlan);
  const industryPremium = orgInd?.pricing?.premium || 0;
  const currentPlanObj  = PLANS.find(p => p.id === currentPlan);
  const monthlyBase    = currentPlanObj?.price || 0;
  const monthlyTotal   = monthlyBase + industryPremium;

  if (loading) return <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading...</div>;

  return (
    <div style={{padding:"32px 36px", maxWidth:1000}}>
      <h1 style={{fontSize:24, fontWeight:800, color:C.heading, marginBottom:4}}>Billing</h1>
      <p style={{fontSize:14, color:C.muted, marginBottom:24}}>Manage your plan, usage, and industry add-ons</p>

      {msg && (
        <div style={{padding:"12px 16px", borderRadius:8, marginBottom:20,
          background: msg.startsWith("✅") ? "#F0FDF4" : "#FEF2F2",
          color: msg.startsWith("✅") ? C.success : C.error, fontSize:14}}>
          {msg}
        </div>
      )}

      {/* Current Usage */}
      {summary && (
        <div style={{background:C.surface, border:`1px solid ${C.border}`,
          borderRadius:12, padding:24, marginBottom:24}}>
          <div style={{display:"flex", justifyContent:"space-between", marginBottom:20}}>
            <div>
              <div style={{fontSize:12,color:C.muted,marginBottom:4}}>Current plan</div>
              <div style={{fontSize:22,fontWeight:800,color:C.primary,textTransform:"capitalize",marginBottom:4}}>
                {currentPlan}
              </div>
              {industryPremium > 0 && (
                <div style={{fontSize:12,color:C.warning}}>
                  {orgInd?.icon} {orgInd?.label} add-on: +₹{industryPremium.toLocaleString()}/month
                </div>
              )}
            </div>
            <div style={{textAlign:"right"}}>
              <div style={{fontSize:12,color:C.muted,marginBottom:4}}>Monthly total</div>
              {monthlyTotal > 0 ? (
                <>
                  <div style={{fontSize:22,fontWeight:800,color:C.heading}}>
                    ₹{monthlyTotal.toLocaleString()}<span style={{fontSize:13,color:C.muted,fontWeight:400}}>/mo</span>
                  </div>
                  <div style={{fontSize:11,color:C.muted}}>
                    +18% GST = ₹{Math.round(monthlyTotal*1.18).toLocaleString()}
                  </div>
                  {industryPremium > 0 && (
                    <div style={{fontSize:11,color:C.muted,marginTop:2}}>
                      Base ₹{monthlyBase.toLocaleString()} + Industry ₹{industryPremium.toLocaleString()}
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

      {/* Plan Cards */}
      <h2 style={{fontSize:17,fontWeight:700,color:C.heading,marginBottom:16}}>Plans</h2>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:16,marginBottom:32}}>
        {PLANS.map(plan => {
          const isCurrent = plan.id === currentPlan;
          const isUpgrade = PLAN_ORDER.indexOf(plan.id) > currentPlanIdx;
          const total     = (plan.price || 0) + (plan.id==="free" ? 0 : industryPremium);

          return (
            <div key={plan.id} style={{
              background: isCurrent ? C.primaryLight : C.surface,
              border: `2px solid ${isCurrent ? C.primary : plan.popular ? C.primary+"44" : C.border}`,
              borderRadius:12, padding:20, position:"relative", display:"flex", flexDirection:"column",
            }}>
              {plan.popular && !isCurrent && (
                <div style={{position:"absolute",top:-10,left:"50%",transform:"translateX(-50%)",
                  background:C.primary,color:"white",fontSize:10,fontWeight:700,
                  padding:"2px 12px",borderRadius:20,whiteSpace:"nowrap"}}>
                  MOST POPULAR
                </div>
              )}
              {isCurrent && (
                <div style={{position:"absolute",top:10,right:10,background:C.primary,
                  color:"white",fontSize:10,fontWeight:700,padding:"2px 8px",borderRadius:20}}>
                  Current
                </div>
              )}

              <div style={{fontSize:16,fontWeight:800,color:C.heading,marginBottom:8,textTransform:"capitalize"}}>
                {plan.label}
              </div>

              <div style={{marginBottom:12}}>
                {plan.id === "enterprise" ? (
                  <span style={{fontSize:20,fontWeight:800,color:C.heading}}>Custom</span>
                ) : plan.price === 0 ? (
                  <span style={{fontSize:20,fontWeight:800,color:C.success}}>Free</span>
                ) : (
                  <>
                    <span style={{fontSize:20,fontWeight:800,color:C.heading}}>
                      ₹{total.toLocaleString()}
                    </span>
                    <span style={{fontSize:11,color:C.muted}}>/month</span>
                    {industryPremium > 0 && plan.id !== "free" && (
                      <div style={{fontSize:10,color:C.warning,marginTop:2}}>
                        incl. ₹{industryPremium.toLocaleString()} industry add-on
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Industry access badge */}
              <div style={{fontSize:11,fontWeight:600,padding:"3px 8px",borderRadius:6,
                background: plan.id==="professional"||plan.id==="enterprise" ? "#E6F0FF" : "#F3F4F6",
                color: plan.id==="professional"||plan.id==="enterprise" ? C.primary : C.muted,
                marginBottom:12, display:"inline-block", alignSelf:"flex-start"}}>
                🏭 {plan.industries[0]}
              </div>

              <div style={{flex:1, marginBottom:16}}>
                {plan.features.map(f => (
                  <div key={f} style={{fontSize:11,color:C.body,padding:"2px 0",
                    display:"flex",gap:4,alignItems:"flex-start"}}>
                    <span style={{color:C.success,flexShrink:0}}>✓</span>
                    <span>{f}</span>
                  </div>
                ))}
              </div>

              {!isCurrent && (
                <button onClick={() => upgrade(plan.id)} disabled={upgrading===plan.id}
                  style={{padding:"8px 0",
                    background: isUpgrade ? C.primary : "#F3F4F6",
                    color: isUpgrade ? "white" : C.muted,
                    border:"none", borderRadius:8, fontSize:12, fontWeight:600,
                    cursor: upgrading===plan.id ? "not-allowed" : "pointer", width:"100%"}}>
                  {upgrading===plan.id ? "Processing..." :
                   plan.id==="enterprise" ? "Contact sales" :
                   isUpgrade ? `Upgrade →` : "Downgrade"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Industry Add-on Banner */}
      <div style={{background:C.primaryLight, border:`1px solid ${C.primary}30`,
        borderRadius:12, padding:20, marginBottom:24,
        display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <div>
          <div style={{fontSize:14,fontWeight:700,color:C.heading,marginBottom:4}}>
            {orgInd?.icon} Industry Add-on: {orgInd?.label || "General / Other"}
          </div>
          <div style={{fontSize:13,color:C.muted}}>
            {industryPremium > 0
              ? `+₹${industryPremium.toLocaleString()}/month — industry-specific risk scoring, clause priorities, playbook templates`
              : "Included in your plan — upgrade industry in Settings for specialized risk scoring"
            }
          </div>
        </div>
        <button onClick={() => window.location.href="/dashboard/settings"}
          style={{padding:"8px 20px", background:C.primary, color:"white",
            borderRadius:8, fontSize:13, fontWeight:600, border:"none",
            whiteSpace:"nowrap", marginLeft:16, cursor:"pointer"}}>
          Change industry →
        </button>
      </div>

      {/* Invoice History */}
      <div style={{background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24}}>
        <h2 style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:16}}>Invoice history</h2>
        {invoices.length === 0
          ? <p style={{color:C.muted,fontSize:14}}>No invoices yet.</p>
          : (
            <table style={{width:"100%",borderCollapse:"collapse"}}>
              <thead>
                <tr>{["Period","Base Plan","Industry Add-on","Total","Status"].map(h => (
                  <th key={h} style={{padding:"8px 0",textAlign:"left",fontSize:12,
                    fontWeight:600,color:C.muted,borderBottom:`1px solid ${C.border}`}}>{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {invoices.map((inv:any) => (
                  <tr key={inv.id} style={{borderBottom:`1px solid ${C.border}`}}>
                    <td style={{padding:"12px 0",fontSize:13,color:C.body}}>
                      {new Date(inv.period_start).toLocaleDateString("en-IN",{month:"short",year:"numeric"})}
                    </td>
                    <td style={{padding:"12px 0",fontSize:13,color:C.body}}>
                      ₹{(inv.base_amount||inv.amount).toLocaleString("en-IN",{maximumFractionDigits:0})}
                    </td>
                    <td style={{padding:"12px 0",fontSize:13,color:C.warning}}>
                      {inv.industry_amount ? `+₹${inv.industry_amount.toLocaleString()}` : "—"}
                    </td>
                    <td style={{padding:"12px 0",fontSize:14,fontWeight:600,color:C.heading}}>
                      ₹{inv.amount.toLocaleString("en-IN",{maximumFractionDigits:2})}
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
