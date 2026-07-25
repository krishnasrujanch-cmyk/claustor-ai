"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  success:"#22C55E", warning:"#F59E0B", error:"#EF4444",
};

export default function SettingsPage() {
  const { user, loadUser } = useAuthStore();
  const [industries, setIndustries] = useState<any[]>([]);
  const [currentIndustry, setCurrentIndustry] = useState<any>(null);
  const [selectedIndustry, setSelectedIndustry] = useState("general");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [pricing, setPricing] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      const token = getToken();
      const h = { Authorization: `Bearer ${token}` };
      try {
        const [indR, orgIndR] = await Promise.all([
          fetch(`${API}/api/v1/industries/`, { headers: h }).then(r => r.json()),
          fetch(`${API}/api/v1/industries/org`, { headers: h }).then(r => r.json()),
        ]);
        // Use available_industries from org endpoint (includes accessibility per plan)
        const inds = orgIndR.available_industries || indR.industries || [];
        setIndustries(inds);
        setCurrentIndustry(orgIndR);
        setSelectedIndustry(orgIndR.industry || "general");

        // Load pricing for current plan
        const plan = user?.plan || "starter";
        const pricingR = await fetch(`${API}/api/v1/industries/pricing?plan=${plan}`, { headers: h }).then(r => r.json());
        setPricing(pricingR.pricing || []);
      } catch(e) { console.error(e); }
    };
    load();
  }, [user?.plan]);

  const saveIndustry = async () => {
    setSaving(true); setMsg("");
    const token = getToken();
    try {
      const r = await fetch(`${API}/api/v1/industries/org`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ industry: selectedIndustry }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail);
      setMsg(`✅ ${d.message}`);
      setCurrentIndustry({ ...currentIndustry, industry: selectedIndustry });
    } catch(e: any) {
      setMsg(`❌ ${e.message}`);
    } finally { setSaving(false); }
  };

  const currentPricingEntry = pricing.find(p => p.industry === selectedIndustry);

  return (
    <div style={{ padding:"32px 36px", maxWidth:800 }}>
      <div style={{ marginBottom:28 }}>
        <h1 style={{ fontSize:24, fontWeight:800, color:C.heading, marginBottom:4 }}>Settings</h1>
        <p style={{ fontSize:14, color:C.muted }}>Organisation preferences and industry configuration</p>
      </div>

      {msg && (
        <div style={{ padding:"12px 16px", borderRadius:8, marginBottom:20,
          background: msg.startsWith("✅") ? "#F0FDF4" : "#FEF2F2",
          color: msg.startsWith("✅") ? C.success : C.error, fontSize:14 }}>
          {msg}
        </div>
      )}

      {/* Industry Setting */}
      <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24, marginBottom:20 }}>
        <div style={{ marginBottom:20 }}>
          <h2 style={{ fontSize:17, fontWeight:700, color:C.heading, marginBottom:4 }}>Industry</h2>
          <p style={{ fontSize:13, color:C.muted }}>
            Sets industry-specific risk scoring thresholds and clause priorities.
            {currentIndustry && (
              <span style={{ marginLeft:8, fontWeight:600, color:C.primary }}>
                Current: {currentIndustry.icon} {currentIndustry.label}
              </span>
            )}
          </p>
        </div>

        {/* Industry grid */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(220px,1fr))", gap:12, marginBottom:20 }}>
          {industries.map(ind => {
            const accessible = ind.accessible !== false;
            return (
            <div key={ind.id}
              onClick={() => accessible && setSelectedIndustry(ind.id)}
              style={{
                padding:"14px 16px",
                border:`2px solid ${selectedIndustry===ind.id?C.primary:accessible?C.border:"#F3F4F6"}`,
                borderRadius:10,
                background: selectedIndustry===ind.id ? C.primaryLight : accessible ? C.surface : "#FAFBFC",
                cursor: accessible ? "pointer" : "not-allowed",
                opacity: accessible ? 1 : 0.6,
                transition:"all 0.15s",
                position:"relative",
              }}>
              {!accessible && (
                <div style={{position:"absolute",top:8,right:8,fontSize:14}}>🔒</div>
              )}
              <div style={{ fontSize:20, marginBottom:6 }}>{ind.icon}</div>
              <div style={{ fontSize:14, fontWeight:700, color:accessible?C.heading:C.muted, marginBottom:2 }}>{ind.label}</div>
              <div style={{ fontSize:12, color:C.muted, marginBottom:8 }}>{ind.description}</div>
              {!accessible ? (
                <span style={{ fontSize:11, fontWeight:600, color:"#9CA3AF",
                  background:"#F3F4F6", padding:"2px 8px", borderRadius:20 }}>
                  Requires {ind.min_plan} plan
                </span>
              ) : ind.premium_inr > 0 ? (
                <span style={{ fontSize:11, fontWeight:600, color:C.warning,
                  background:"#FFFBEB", padding:"2px 8px", borderRadius:20 }}>
                  +₹{ind.premium_inr.toLocaleString()}/month
                </span>
              ) : (
                <span style={{ fontSize:11, fontWeight:600, color:C.success,
                  background:"#F0FDF4", padding:"2px 8px", borderRadius:20 }}>
                  Included
                </span>
              )}
            </div>
            );
          })}
        </div>

        {/* Pricing preview */}
        {currentPricingEntry && currentPricingEntry.premium > 0 && (
          <div style={{ padding:"12px 16px", background:C.primaryLight, borderRadius:8,
            border:`1px solid ${C.primary}30`, marginBottom:16 }}>
            <div style={{ fontSize:13, color:C.primary, fontWeight:600, marginBottom:4 }}>
              Pricing with this industry:
            </div>
            <div style={{ fontSize:13, color:C.body }}>
              {user?.plan?.charAt(0).toUpperCase()}{user?.plan?.slice(1)} plan (₹{currentPricingEntry.base_price.toLocaleString()})
              + {industries.find(i=>i.id===selectedIndustry)?.label} premium (₹{currentPricingEntry.premium.toLocaleString()})
              = <strong>₹{currentPricingEntry.total.toLocaleString()}/month</strong>
              <span style={{ color:C.muted }}> + 18% GST = ₹{currentPricingEntry.total_gst.toLocaleString()}</span>
            </div>
          </div>
        )}

        <button onClick={saveIndustry} disabled={saving}
          style={{ padding:"10px 24px", background:C.primary, color:"white",
            border:"none", borderRadius:8, fontSize:14, fontWeight:600,
            cursor:saving?"not-allowed":"pointer" }}>
          {saving ? "Saving..." : "Save industry setting"}
        </button>
      </div>

      {/* Current industry features */}
      {currentIndustry && currentIndustry.high_risk_clauses?.length > 0 && (
        <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24, marginBottom:20 }}>
          <h2 style={{ fontSize:16, fontWeight:700, color:C.heading, marginBottom:16 }}>
            {currentIndustry.icon} {currentIndustry.label} — Risk Configuration
          </h2>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <div>
              <div style={{ fontSize:13, fontWeight:600, color:C.body, marginBottom:8 }}>
                🔴 High-risk clause types
              </div>
              {currentIndustry.high_risk_clauses.map((c: string) => (
                <div key={c} style={{ fontSize:12, color:C.muted, padding:"3px 0",
                  borderBottom:`1px solid ${C.border}` }}>
                  {c.replace(/_/g, " ")}
                </div>
              ))}
            </div>
            <div>
              <div style={{ fontSize:13, fontWeight:600, color:C.body, marginBottom:8 }}>
                ⚠️ Critical missing clauses
              </div>
              {currentIndustry.critical_missing.map((c: string) => (
                <div key={c} style={{ fontSize:12, color:C.muted, padding:"3px 0",
                  borderBottom:`1px solid ${C.border}` }}>
                  {c.replace(/_/g, " ")}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Org Info */}
      <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
        <h2 style={{ fontSize:16, fontWeight:700, color:C.heading, marginBottom:16 }}>Organisation</h2>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
          {[
            { label:"Email",    value: user?.email },
            { label:"Role",     value: user?.role?.replace(/_/g," ") },
            { label:"Plan",     value: user?.plan?.toUpperCase() },
            { label:"Industry", value: currentIndustry?.label || "General" },
          ].map(item => (
            <div key={item.label}>
              <div style={{ fontSize:12, color:C.muted, marginBottom:4 }}>{item.label}</div>
              <div style={{ fontSize:14, fontWeight:600, color:C.heading }}>{item.value || "—"}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
