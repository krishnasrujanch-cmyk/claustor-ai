"use client";
export const dynamic = "force-dynamic";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";

// ── Claustor Brand Tokens ─────────────────────────────────────────────────
const C = {
  primary:       "#0066FF",
  primaryDark:   "#0052CC",
  primaryLight:  "#EFF6FF",
  primaryGlow:   "rgba(0,102,255,0.15)",
  heading:       "#111827",
  body:          "#374151",
  muted:         "#6B7280",
  border:        "#E5E7EB",
  surface:       "#FFFFFF",
  bg:            "#FAFBFC",
  dark:          "#0D0F1A",
  darkSurface:   "#161827",
  darkBorder:    "#2D3148",
  success:       "#22C55E",
  warning:       "#F59E0B",
  error:         "#EF4444",
};

// ── Exchange rate (update periodically) ──────────────────────────────────
const USD_RATE = 84;

// ── Plans ─────────────────────────────────────────────────────────────────
const PLANS = [
  {
    id:       "free",
    name:     "Free",
    priceINR: 0,
    period:   "forever",
    tagline:  "Try before you buy",
    color:    C.muted,
    contracts: "5",
    queries:   "100",
    users:     "1",
    features: [
      "5 contracts/month",
      "100 AI queries/month",
      "PDF support",
      "Community support",
    ],
    cta: "Start Free",
    ctaLink: "/register",
    popular: false,
  },
  {
    id:       "starter",
    name:     "Starter",
    priceINR: 7999,
    period:   "month",
    tagline:  "For small legal teams",
    color:    C.primary,
    contracts: "100",
    queries:   "5,000",
    users:     "5",
    features: [
      "100 contracts/month",
      "5,000 AI queries/month",
      "PDF, DOCX, XLS support",
      "5 users included",
      "Vision AI (scanned docs)",
      "Email support",
      "₹800/extra user",
    ],
    cta: "Get Started",
    ctaLink: "/register?plan=starter",
    popular: false,
  },
  {
    id:       "professional",
    name:     "Professional",
    priceINR: 29999,
    period:   "month",
    tagline:  "For growing businesses",
    color:    C.primary,
    contracts: "500",
    queries:   "25,000",
    users:     "25",
    features: [
      "500 contracts/month",
      "25,000 AI queries/month",
      "All formats + OCR",
      "25 users included",
      "Smart AI routing (Groq + Haiku + Sonnet)",
      "Industry pack add-on",
      "Priority support",
      "₹1,500/extra user",
    ],
    cta: "Start Trial",
    ctaLink: "/register?plan=professional",
    popular: true,
  },
  {
    id:       "enterprise",
    name:     "Enterprise",
    priceINR: 99999,
    period:   "month",
    tagline:  "For large organisations",
    color:    "#92400E",
    contracts: "Unlimited",
    queries:   "Unlimited",
    users:     "Unlimited",
    features: [
      "Unlimited contracts & queries",
      "Unlimited users",
      "Sonnet AI (30% of queries)",
      "Dedicated Celery queue",
      "Custom Pinecone namespace",
      "SSO / SAML",
      "Audit log export",
      "API access",
      "Dedicated SLA + onboarding",
      "Industry pack included",
    ],
    cta: "Contact Sales",
    ctaLink: "/contact",
    popular: false,
    custom: true,
  },
];

// ── Business value props ───────────────────────────────────────────────────
const VALUES = [
  {
    icon: "⚡",
    title: "Reduce Legal Review Time",
    desc: "Up to 80% faster contract review. AI extracts clauses, flags risks, and summarises obligations in seconds — not days.",
    stat: "80%",
    statLabel: "faster review",
  },
  {
    icon: "🔔",
    title: "Never Miss a Renewal",
    desc: "Automatic obligation and renewal tracking. Get alerts 15, 7, and 3 days before critical deadlines.",
    stat: "0",
    statLabel: "missed renewals",
  },
  {
    icon: "🛡️",
    title: "Detect Hidden Risks",
    desc: "AI identifies risky clauses, missing protections, and unusual terms before you sign — across 25 clause types.",
    stat: "25",
    statLabel: "clause types",
  },
  {
    icon: "💬",
    title: "Ask Anything Naturally",
    desc: "Chat with your contracts in plain English. Ask about GSTINs, SLA credits, payment terms, exit clauses — get instant answers.",
    stat: "8",
    statLabel: "countries supported",
  },
];

// ── Logo component — official Claustor logo ─────────────────────────────
function Logo({ height = 52 }: { height?: number }) {
  const width = height * (450 / 110);
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 110" width={width} height={height}>
      <defs>
        <linearGradient id="claustorRingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8B5CF6"/>
          <stop offset="50%" stopColor="#3B82F6"/>
          <stop offset="100%" stopColor="#06B6D4"/>
        </linearGradient>
        <linearGradient id="claustorCGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#06B6D4"/>
          <stop offset="100%" stopColor="#0066FF"/>
        </linearGradient>
        <linearGradient id="lighterDocBg" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#475569"/>
          <stop offset="100%" stopColor="#334155"/>
        </linearGradient>
      </defs>
      <g transform="translate(10, 5)">
        <path d="M 68 28 A 40 40 0 1 0 68 72"
          fill="none" stroke="url(#claustorRingGradient)"
          strokeWidth="11" strokeLinecap="round"/>
        <line x1="68" y1="28" x2="80" y2="28" stroke="#3B82F6" strokeWidth="5" strokeLinecap="round"/>
        <circle cx="76" cy="28" r="5" fill="#3B82F6"/>
        <circle cx="86" cy="28" r="3.5" fill="#06B6D4"/>
        <line x1="68" y1="72" x2="80" y2="72" stroke="#06B6D4" strokeWidth="5" strokeLinecap="round"/>
        <circle cx="76" cy="72" r="5" fill="#06B6D4"/>
        <circle cx="86" cy="72" r="3.5" fill="#0066FF"/>
        <rect x="30" y="31" width="28" height="38" rx="5"
          fill="url(#lighterDocBg)" stroke="#64748B" strokeWidth="1.5"/>
        <line x1="36" y1="40" x2="52" y2="40" stroke="#F1F5F9" strokeWidth="2" strokeLinecap="round"/>
        <line x1="36" y1="46" x2="52" y2="46" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round"/>
        <line x1="36" y1="52" x2="52" y2="52" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round"/>
        <line x1="36" y1="58" x2="46" y2="58" stroke="#38BDF8" strokeWidth="2" strokeLinecap="round"/>
      </g>
      <g transform="translate(122, 0)">
        <text x="0" y="62" fontFamily="Inter, system-ui, sans-serif" fontSize="48" fontWeight="800" letterSpacing="-0.5">
          <tspan fill="url(#claustorCGradient)">C</tspan>
          <tspan fill="#111827">laustor</tspan>
        </text>
        <text x="2" y="86" fontFamily="Inter, system-ui, sans-serif" fontSize="19" fontWeight="400" fill="#6B7280" letterSpacing="0.3">
          AI Contract Intelligence
        </text>
      </g>
    </svg>
  );
}

// ── International contact popup ───────────────────────────────────────────
function IntlPopup({ onClose }: { onClose: () => void }) {
  const [sent, setSent] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", company: "", country: "", size: "" });

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{ background: "white", borderRadius: 16, padding: 32, maxWidth: 460, width: "90%", boxShadow: "0 24px 80px rgba(0,0,0,0.3)" }}>
        {sent ? (
          <div style={{ textAlign: "center", padding: "24px 0" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: C.heading, marginBottom: 8 }}>We'll be in touch!</div>
            <div style={{ fontSize: 14, color: C.muted }}>Our team will reach out within 24 hours with pricing in your currency.</div>
            <button onClick={onClose} style={{ marginTop: 24, padding: "10px 28px", background: C.primary, color: "white", border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 600 }}>Close</button>
          </div>
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700, color: C.heading }}>International Pricing</div>
                <div style={{ fontSize: 13, color: C.muted, marginTop: 4 }}>Get pricing in USD, GBP, SGD, AED, or AUD</div>
              </div>
              <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: C.muted }}>✕</button>
            </div>
            {[
              { key: "name", label: "Full Name", placeholder: "Jane Smith" },
              { key: "email", label: "Work Email", placeholder: "jane@company.com" },
              { key: "company", label: "Company", placeholder: "Acme Legal Ltd" },
              { key: "country", label: "Country", placeholder: "United Kingdom" },
            ].map(({ key, label, placeholder }) => (
              <div key={key} style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: C.body, display: "block", marginBottom: 4 }}>{label}</label>
                <input
                  placeholder={placeholder}
                  value={(form as any)[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  style={{ width: "100%", padding: "9px 12px", border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 13, boxSizing: "border-box" }}
                />
              </div>
            ))}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: C.body, display: "block", marginBottom: 4 }}>Team Size</label>
              <select value={form.size} onChange={e => setForm(f => ({ ...f, size: e.target.value }))}
                style={{ width: "100%", padding: "9px 12px", border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 13, background: "white" }}>
                <option value="">Select...</option>
                <option value="1-5">1–5 people</option>
                <option value="6-25">6–25 people</option>
                <option value="26-100">26–100 people</option>
                <option value="100+">100+ people</option>
              </select>
            </div>
            <button
              onClick={() => setSent(true)}
              style={{ width: "100%", padding: "12px", background: C.primary, color: "white", border: "none", borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
              Get International Pricing →
            </button>
            <div style={{ fontSize: 11, color: C.muted, textAlign: "center", marginTop: 10 }}>
              Your request goes to sales@claustor.ai · Response within 24 hours
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── Animated counter ──────────────────────────────────────────────────────
function Counter({ target, suffix = "" }: { target: number; suffix?: string }) {
  const [val, setVal] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        let start = 0;
        const step = target / 40;
        const timer = setInterval(() => {
          start += step;
          if (start >= target) { setVal(target); clearInterval(timer); }
          else setVal(Math.floor(start));
        }, 30);
      }
    }, { threshold: 0.5 });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target]);
  return <span ref={ref}>{val.toLocaleString()}{suffix}</span>;
}


// ── Demo Request Popup ────────────────────────────────────────────────────
function DemoPopup({ onClose }: { onClose: () => void }) {
  const [sent, setSent] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", company: "", size: "", usecase: "" });

  const handleSubmit = async () => {
    try {
      await fetch("http://localhost:8000/api/v1/billing/enterprise/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: form.company,
          contact_name: form.name,
          business_email: form.email,
          company_size: form.size,
          message: `Demo request. Use case: ${form.usecase}`,
          industry: form.usecase,
        }),
      });
    } catch {}
    setSent(true);
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 1000,
      display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(4px)" }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: "white", borderRadius: 20, padding: 36, maxWidth: 480,
        width: "90%", boxShadow: "0 32px 80px rgba(0,0,0,0.4)" }}>
        {sent ? (
          <div style={{ textAlign: "center", padding: "24px 0" }}>
            <div style={{ fontSize: 52, marginBottom: 16 }}>🎉</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: "#111827", marginBottom: 8 }}>Demo Booked!</div>
            <div style={{ fontSize: 14, color: "#6B7280", lineHeight: 1.6 }}>
              Our team will reach out within <strong>4 business hours</strong> to schedule your personalised walkthrough.
            </div>
            <button onClick={onClose} style={{ marginTop: 24, padding: "12px 32px",
              background: "#0066FF", color: "white", border: "none", borderRadius: 10,
              cursor: "pointer", fontWeight: 700, fontSize: 15 }}>
              Got it →
            </button>
          </div>
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
              <div>
                <div style={{ fontSize: 22, fontWeight: 800, color: "#111827", marginBottom: 4 }}>
                  Book a Live Demo
                </div>
                <div style={{ fontSize: 14, color: "#6B7280" }}>
                  See Claustor analyse a real contract in under 30 seconds.
                </div>
              </div>
              <button onClick={onClose} style={{ background: "none", border: "none",
                fontSize: 22, cursor: "pointer", color: "#9CA3AF", lineHeight: 1 }}>✕</button>
            </div>

            {/* What you'll see */}
            <div style={{ background: "#F0F7FF", border: "1px solid #DBEAFE", borderRadius: 12,
              padding: "12px 16px", marginBottom: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#0066FF", marginBottom: 8 }}>
                IN YOUR DEMO YOU'LL SEE:
              </div>
              {[
                "Upload a contract — analyzed in under 30 seconds",
                "Ask questions in plain English, get cited answers",
                "See risk clauses flagged automatically",
                "Live Q&A: ask anything about the contract",
              ].map(item => (
                <div key={item} style={{ display: "flex", gap: 8, marginBottom: 5, fontSize: 13, color: "#374151" }}>
                  <span style={{ color: "#22C55E", fontWeight: 700 }}>✓</span>{item}
                </div>
              ))}
            </div>

            {[
              { key: "name", label: "Full Name *", placeholder: "Jane Smith" },
              { key: "email", label: "Work Email *", placeholder: "jane@company.com" },
              { key: "company", label: "Company *", placeholder: "Acme Legal Ltd" },
            ].map(({ key, label, placeholder }) => (
              <div key={key} style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#374151",
                  display: "block", marginBottom: 4 }}>{label}</label>
                <input
                  placeholder={placeholder}
                  value={(form as any)[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  style={{ width: "100%", padding: "10px 12px", border: "1px solid #E5E7EB",
                    borderRadius: 8, fontSize: 13, boxSizing: "border-box",
                    outline: "none" }}
                />
              </div>
            ))}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#374151", display: "block", marginBottom: 4 }}>Team Size</label>
                <select value={form.size} onChange={e => setForm(f => ({ ...f, size: e.target.value }))}
                  style={{ width: "100%", padding: "10px 12px", border: "1px solid #E5E7EB",
                    borderRadius: 8, fontSize: 13, background: "white" }}>
                  <option value="">Select...</option>
                  <option>1–5 people</option>
                  <option>6–25 people</option>
                  <option>26–100 people</option>
                  <option>100+ people</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#374151", display: "block", marginBottom: 4 }}>Primary Use Case</label>
                <select value={form.usecase} onChange={e => setForm(f => ({ ...f, usecase: e.target.value }))}
                  style={{ width: "100%", padding: "10px 12px", border: "1px solid #E5E7EB",
                    borderRadius: 8, fontSize: 13, background: "white" }}>
                  <option value="">Select...</option>
                  <option>Reviewing contracts faster</option>
                  <option>Catching risky clauses</option>
                  <option>Tracking renewals & obligations</option>
                  <option>Managing vendor contracts</option>
                  <option>Something else</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={!form.name || !form.email || !form.company}
              style={{ width: "100%", padding: "13px", background: "#0066FF",
                color: "white", border: "none", borderRadius: 10, fontSize: 15,
                fontWeight: 700, cursor: "pointer",
                opacity: (!form.name || !form.email || !form.company) ? 0.5 : 1 }}>
              Book My Demo →
            </button>
            <div style={{ fontSize: 11, color: "#9CA3AF", textAlign: "center", marginTop: 10 }}>
              Your request goes to sales@claustor.ai · We respond within 4 business hours
            </div>
          </>
        )}
      </div>
    </div>
  );
}


// ── Enterprise Contact Popup (Landing Page) ───────────────────────────────
function EnterprisePopup({ onClose }: { onClose: () => void }) {
  const [sent, setSent] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", company: "", size: "", message: "" });

  const handleSubmit = async () => {
    try {
      await fetch("http://localhost:8000/api/v1/billing/enterprise/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name:  form.company,
          contact_name:   form.name,
          business_email: form.email,
          company_size:   form.size,
          message:        form.message || "Enterprise plan inquiry from landing page",
          industry:       "enterprise",
        }),
      });
    } catch {}
    setSent(true);
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 1000,
      display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(4px)" }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: "white", borderRadius: 20, padding: 36, maxWidth: 500,
        width: "90%", boxShadow: "0 32px 80px rgba(0,0,0,0.4)" }}>
        {sent ? (
          <div style={{ textAlign: "center", padding: "24px 0" }}>
            <div style={{ fontSize: 52, marginBottom: 16 }}>��</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: "#111827", marginBottom: 8 }}>We'll be in touch!</div>
            <div style={{ fontSize: 14, color: "#6B7280", lineHeight: 1.6 }}>
              Our enterprise team will reach out within <strong>4 business hours</strong> with a custom quote tailored to your needs.
            </div>
            <button onClick={onClose} style={{ marginTop: 24, padding: "12px 32px",
              background: "#0066FF", color: "white", border: "none", borderRadius: 10,
              cursor: "pointer", fontWeight: 700, fontSize: 15 }}>Got it →</button>
          </div>
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
              <div>
                <div style={{ fontSize: 22, fontWeight: 800, color: "#111827", marginBottom: 4 }}>Talk to Sales</div>
                <div style={{ fontSize: 13, color: "#6B7280" }}>Tell us about your team — we'll get back within 4 hours</div>
              </div>
              <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 22, cursor: "pointer", color: "#9CA3AF" }}>✕</button>
            </div>

            {/* Includes */}
            <div style={{ background: "#F0F7FF", border: "1px solid #DBEAFE", borderRadius: 12, padding: "14px 16px", marginBottom: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#0066FF", marginBottom: 8 }}>ENTERPRISE INCLUDES:</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 16px" }}>
                {[
                  "Unlimited contracts & queries",
                  "Sonnet AI (30% of queries)",
                  "Dedicated processing queue",
                  "Custom data namespace",
                  "SSO / SAML",
                  "Audit log export",
                  "API access + Webhooks",
                  "Industry pack included",
                  "SLA 99.9% uptime",
                  "Dedicated onboarding",
                ].map(f => (
                  <div key={f} style={{ display: "flex", gap: 6, fontSize: 12, color: "#374151", marginBottom: 3 }}>
                    <span style={{ color: "#22C55E", fontWeight: 700 }}>✓</span>{f}
                  </div>
                ))}
              </div>
            </div>

            {[
              { key: "name", label: "Full Name *", ph: "Jane Smith" },
              { key: "email", label: "Work Email *", ph: "jane@company.com" },
              { key: "company", label: "Company *", ph: "Acme Corp" },
            ].map(({ key, label, ph }) => (
              <div key={key} style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#374151", display: "block", marginBottom: 4 }}>{label}</label>
                <input placeholder={ph} value={(form as any)[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  style={{ width: "100%", padding: "10px 12px", border: "1px solid #E5E7EB", borderRadius: 8, fontSize: 13, boxSizing: "border-box" }} />
              </div>
            ))}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#374151", display: "block", marginBottom: 4 }}>Team Size</label>
                <select value={form.size} onChange={e => setForm(f => ({ ...f, size: e.target.value }))}
                  style={{ width: "100%", padding: "10px 12px", border: "1px solid #E5E7EB", borderRadius: 8, fontSize: 13, background: "white" }}>
                  <option value="">Select...</option>
                  <option>1–25 people</option>
                  <option>26–100 people</option>
                  <option>100–500 people</option>
                  <option>500+ people</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#374151", display: "block", marginBottom: 4 }}>Country</label>
                <select value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                  style={{ width: "100%", padding: "10px 12px", border: "1px solid #E5E7EB", borderRadius: 8, fontSize: 13, background: "white" }}>
                  <option value="">Select...</option>
                  <option>India</option>
                  <option>United Kingdom</option>
                  <option>United States</option>
                  <option>Singapore</option>
                  <option>Australia</option>
                  <option>UAE</option>
                  <option>Other</option>
                </select>
              </div>
            </div>

            <button onClick={handleSubmit}
              disabled={!form.name || !form.email || !form.company}
              style={{ width: "100%", padding: "13px", background: "#0066FF", color: "white",
                border: "none", borderRadius: 10, fontSize: 15, fontWeight: 700, cursor: "pointer",
                opacity: (!form.name || !form.email || !form.company) ? 0.5 : 1 }}>
              Send Message →
            </button>
            <div style={{ fontSize: 11, color: "#9CA3AF", textAlign: "center", marginTop: 10 }}>
              Goes to sales@claustor.ai · Response within 4 business hours
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── FAQ Item ──────────────────────────────────────────────────────────────
function FAQItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ borderBottom: "1px solid #E5E7EB", padding: "20px 0" }}>
      <button onClick={() => setOpen(!open)} style={{
        width: "100%", display: "flex", justifyContent: "space-between",
        alignItems: "center", background: "none", border: "none",
        cursor: "pointer", textAlign: "left", padding: 0,
      }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: "#111827" }}>{question}</span>
        <span style={{ fontSize: 20, color: "#6B7280", flexShrink: 0, marginLeft: 16,
          transform: open ? "rotate(45deg)" : "none", transition: "transform 0.2s" }}>+</span>
      </button>
      {open && (
        <p style={{ fontSize: 14, color: "#6B7280", lineHeight: 1.7, margin: "12px 0 0" }}>{answer}</p>
      )}
    </div>
  );
}

// ── Main Landing Page ──────────────────────────────────────────────────────
export default function LandingPage() {
  const [currency, setCurrency] = useState<"INR" | "USD">("INR");
  const [showIntl, setShowIntl] = useState(false);
  const [showDemo, setShowDemo] = useState(false);
  const [showEnterprise, setShowEnterprise] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const fmt = (inr: number) =>
    currency === "INR"
      ? `₹${inr.toLocaleString("en-IN")}`
      : `$${Math.round(inr / USD_RATE).toLocaleString()}`;

  return (
    <div style={{ fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif", color: C.body, background: C.bg, minHeight: "100vh" }}>

      {/* ── NAVBAR ──────────────────────────────────────────────── */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        background: "rgba(255,255,255,0.98)",
        backdropFilter: "blur(12px)",
        borderBottom: `1px solid ${C.border}`,
        padding: "0 5vw",
      }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", height: 64 }}>
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Logo height={52} />
            
          </div>

          {/* Nav links */}
          <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
            {["Features", "Pricing", "Security", "Docs"].map(item => (
              <a key={item} href={`#${item.toLowerCase()}`}
                style={{ fontSize: 14, fontWeight: 500, color: C.body, textDecoration: "none" }}>
                {item}
              </a>
            ))}
          </div>

          {/* CTA */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Link href="/login" style={{ fontSize: 14, fontWeight: 600, color: C.body, textDecoration: "none" }}>Sign in</Link>
            <Link href="/register" style={{
              fontSize: 14, fontWeight: 700, background: C.primary, color: "white",
              padding: "9px 20px", borderRadius: 8, textDecoration: "none",
              boxShadow: `0 4px 14px ${C.primaryGlow}`,
            }}>
              Start Free →
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ────────────────────────────────────────────────── */}
      <section style={{
        background: `linear-gradient(160deg, ${C.dark} 0%, ${C.darkSurface} 40%, #1a1b35 100%)`,
        padding: "160px 5vw 100px",
        position: "relative",
        overflow: "hidden",
      }}>
        {/* Rotating word animation */}
      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:none} }
        @keyframes typingDot { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-4px)} }
      `}</style>
      {/* Background glow orbs */}
        <div style={{ position: "absolute", top: "20%", left: "10%", width: 500, height: 500, background: `radial-gradient(circle, ${C.primaryGlow} 0%, transparent 70%)`, pointerEvents: "none" }} />
        <div style={{ position: "absolute", top: "40%", right: "5%", width: 300, height: 300, background: "radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)", pointerEvents: "none" }} />

        <div style={{ maxWidth: 1200, margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, alignItems: "center" }}>
          {/* Left — copy */}
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "rgba(91,75,255,0.2)", border: "1px solid rgba(91,75,255,0.4)", borderRadius: 20, padding: "6px 14px", marginBottom: 24 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: C.success, display: "inline-block", animation: "pulse 2s infinite" }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: "#A5B4FC" }}>Enterprise AI · Now in Beta</span>
            </div>

            <h1 style={{ fontSize: "clamp(36px, 5vw, 60px)", fontWeight: 900, color: "white", lineHeight: 1.1, letterSpacing: "-2px", margin: "0 0 8px" }}>
              Transforming<br />
              Contracts into
            </h1>
            <h1 style={{
              fontSize: "clamp(36px, 5vw, 60px)", fontWeight: 900, lineHeight: 1.1,
              letterSpacing: "-2px", margin: "0 0 20px",
              background: "linear-gradient(135deg, #0066FF 0%, #06B6D4 60%, #38BDF8 100%)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              filter: "drop-shadow(0 0 20px rgba(0,102,255,0.4))",
            }}>
              Actionable Intelligence
            </h1>

            <p style={{ fontSize: 18, color: "#9CA3AF", lineHeight: 1.7, maxWidth: 480, margin: "0 0 36px" }}>
              Analyse contracts in seconds, detect hidden risks, compare agreements, and get AI-powered answers — all from one enterprise platform.
            </p>

            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <Link href="/register" style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: C.primary, color: "white", fontWeight: 700, fontSize: 16,
                padding: "14px 28px", borderRadius: 10, textDecoration: "none",
                boxShadow: `0 8px 32px ${C.primaryGlow}`,
              }}>
                Start Free — No credit card
                <span>→</span>
              </Link>
              <a href="#" onClick={(e)=>{e.preventDefault();setShowDemo(true);}} style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "rgba(255,255,255,0.08)", color: "white", fontWeight: 600, fontSize: 16,
                padding: "14px 28px", borderRadius: 10, textDecoration: "none",
                border: "1px solid rgba(255,255,255,0.15)",
              }}>
                📅 Book a Demo
              </a>
            </div>

            {/* Trust signals */}
            <div style={{ display: "flex", gap: 24, marginTop: 36 }}>
              {[
                { icon: "🔒", text: "SOC 2 Ready" },
                { icon: "🌍", text: "8 Countries" },
                { icon: "⚡", text: "Under 3s response" },
              ].map(({ icon, text }) => (
                <div key={text} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 14 }}>{icon}</span>
                  <span style={{ fontSize: 12, color: "#6B7280", fontWeight: 500 }}>{text}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right — dashboard preview */}
          <div style={{
            background: C.darkSurface,
            border: `1px solid ${C.darkBorder}`,
            borderRadius: 16,
            padding: 20,
            boxShadow: "0 32px 80px rgba(0,0,0,0.5)",
          }}>
            {/* Mock copilot chat */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${C.darkBorder}` }}>
              <Logo height={36} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "white" }}>Claustor AI Copilot</span>
              <span style={{ marginLeft: "auto", fontSize: 10, background: "rgba(34,197,94,0.15)", color: C.success, padding: "2px 8px", borderRadius: 20, fontWeight: 600 }}>● Live</span>
            </div>
            {[
              { q: "What is the supplier's GSTIN?", a: "Northwind Cloud Technologies\nGSTIN: 29AAJCN4417K1ZP ✓", type: "id" },
              { q: "List SLAs with credits", a: "SL-01: 99.95% uptime → 4% credit\nSL-04: Sev1 resolve 4hrs → 5% credit\nMax 15% monthly cap", type: "table" },
              { q: "Any contracts expiring in 30 days?", a: "2 contracts expiring soon:\n• Pharma MSA — Aug 31 ⚠️\n• IT Outsourcing — Sep 12", type: "alert" },
            ].map(({ q, a, type }, i) => (
              <div key={i} style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 6 }}>
                  <div style={{ background: C.primary, color: "white", fontSize: 12, padding: "8px 12px", borderRadius: "12px 12px 4px 12px", maxWidth: "80%" }}>
                    {q}
                  </div>
                </div>
                <div style={{ background: "rgba(255,255,255,0.05)", color: "#D1D5DB", fontSize: 12, padding: "10px 12px", borderRadius: "4px 12px 12px 12px", whiteSpace: "pre-line", borderLeft: `3px solid ${type === "alert" ? C.warning : type === "id" ? C.success : C.primary}` }}>
                  {a}
                </div>
              </div>
            ))}
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
              <input readOnly value="Ask anything about your contracts..." style={{ flex: 1, background: "rgba(255,255,255,0.05)", border: `1px solid ${C.darkBorder}`, borderRadius: 8, padding: "8px 12px", fontSize: 12, color: "#6B7280" }} />
              <div style={{ width: 32, height: 32, background: C.primary, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
                <span style={{ color: "white", fontSize: 14 }}>↑</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── BUILT FOR ──────────────────────────────────────────── */}
      <section style={{ background: C.surface, borderBottom: `1px solid ${C.border}`, padding: "20px 5vw" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", alignItems: "center", gap: 32, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: C.muted, whiteSpace: "nowrap" }}>BUILT FOR</span>
          {["Legal Teams", "Procurement", "Finance", "Sales", "Compliance", "Enterprises"].map(team => (
            <div key={team} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ color: C.success, fontSize: 14, fontWeight: 700 }}>✓</span>
              <span style={{ fontSize: 14, fontWeight: 500, color: C.body }}>{team}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── BUSINESS VALUE ─────────────────────────────────────── */}
      <section id="features" style={{ padding: "100px 5vw", background: C.bg }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: C.primary, letterSpacing: "1.5px", textTransform: "uppercase" }}>Why Claustor</span>
            <h2 style={{ fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 900, color: C.heading, letterSpacing: "-1.5px", margin: "12px 0 16px" }}>
              Business Problems We Solve
            </h2>
            <p style={{ fontSize: 17, color: C.muted, maxWidth: 540, margin: "0 auto", lineHeight: 1.6 }}>
              Real outcomes for legal and commercial teams. Not AI for its own sake.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 24 }}>
            {VALUES.map(({ icon, title, desc, stat, statLabel }) => (
              <div key={title} style={{
                background: C.surface,
                border: `1px solid ${C.border}`,
                borderRadius: 16,
                padding: 28,
                transition: "transform 0.2s, box-shadow 0.2s",
              }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.transform = "translateY(-4px)"; (e.currentTarget as HTMLDivElement).style.boxShadow = `0 12px 40px ${C.primaryGlow}`; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.transform = "none"; (e.currentTarget as HTMLDivElement).style.boxShadow = "none"; }}>
                <div style={{ fontSize: 32, marginBottom: 16 }}>{icon}</div>
                <div style={{ fontSize: 28, fontWeight: 900, color: C.primary, letterSpacing: "-1px", marginBottom: 4 }}>
                  <Counter target={parseInt(stat)} suffix={stat.includes("%") ? "%" : "+"} />
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: C.muted, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.5px" }}>{statLabel}</div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: C.heading, marginBottom: 8 }}>{title}</h3>
                <p style={{ fontSize: 14, color: C.muted, lineHeight: 1.6, margin: 0 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ────────────────────────────────────────── */}
      <section style={{ padding: "80px 5vw", background: C.surface, borderTop: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 900, margin: "0 auto", textAlign: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: C.primary, letterSpacing: "1.5px", textTransform: "uppercase" }}>How It Works</span>
          <h2 style={{ fontSize: "clamp(26px, 3.5vw, 40px)", fontWeight: 900, color: C.heading, letterSpacing: "-1px", margin: "12px 0 48px" }}>
            From upload to insight in under 30 seconds
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 0, position: "relative" }}>
            {/* Connecting line */}
            <div style={{ position: "absolute", top: 28, left: "16%", right: "16%", height: 2, background: `linear-gradient(90deg, ${C.primary}, #A78BFA)`, zIndex: 0 }} />
            {[
              { num: "01", title: "Upload", desc: "PDF, DOCX, scanned docs, or images. Any format, any language.", icon: "📄" },
              { num: "02", title: "AI Analyses", desc: "Extracts 25 clause types, scores risk, identifies parties and obligations.", icon: "🧠" },
              { num: "03", title: "Ask Anything", desc: "Chat naturally. Get grounded answers with citations from your contract.", icon: "💬" },
            ].map(({ num, title, desc, icon }) => (
              <div key={num} style={{ position: "relative", zIndex: 1, padding: "0 20px" }}>
                <div style={{ width: 56, height: 56, borderRadius: "50%", background: C.primary, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px", fontSize: 22, boxShadow: `0 8px 24px ${C.primaryGlow}` }}>
                  {icon}
                </div>
                <div style={{ fontSize: 11, fontWeight: 700, color: C.primary, letterSpacing: "1px", marginBottom: 8 }}>{num}</div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: C.heading, marginBottom: 8 }}>{title}</h3>
                <p style={{ fontSize: 14, color: C.muted, lineHeight: 1.6 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>


      {/* ── COMPARISON TABLE ────────────────────────────────────── */}
      <section style={{ padding: "100px 5vw", background: C.bg }}>
        <div style={{ maxWidth: 960, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: C.primary, letterSpacing: "1.5px", textTransform: "uppercase" }}>Why Claustor</span>
            <h2 style={{ fontSize: "clamp(26px, 3.5vw, 40px)", fontWeight: 900, color: C.heading, letterSpacing: "-1px", margin: "12px 0" }}>
              Claustor vs Manual Review vs Traditional CLM
            </h2>
          </div>
          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 16, overflow: "hidden" }}>
            <div style={{ display: "grid", gridTemplateColumns: "2.5fr 1fr 1.2fr 1.2fr", background: "#111827" }}>
              {["Capability", "Manual", "Traditional CLM", "Claustor AI"].map((h, i) => (
                <div key={h} style={{ padding: "14px 20px", fontSize: 12, fontWeight: 700,
                  color: i === 3 ? "#06B6D4" : "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.5px" }}>{h}</div>
              ))}
            </div>
            {[
              ["AI-Powered Search", "❌", "⚠️ Limited", "✅ BM25 + Vector + RRF"],
              ["Natural Language Q&A", "❌", "❌", "✅ Citation-verified answers"],
              ["Risk Detection", "⚠️ Manual", "⚠️ Basic rules", "✅ 25 clause types"],
              ["Clause Comparison", "❌", "❌", "✅ Cross-contract analysis"],
              ["Multi-language Support", "❌", "⚠️ Limited", "✅ Multilingual (bge-m3)"],
              ["Party ID Extraction", "❌", "❌", "✅ 8 countries, 25+ ID types"],
              ["Vision AI (Scanned Docs)", "❌", "❌", "✅ OCR + image tables"],
              ["Bulk Import", "❌", "⚠️ Limited", "✅ ZIP batch upload"],
              ["Industry Risk Scoring", "❌", "❌", "✅ 8 industry playbooks"],
              ["Missing Clause Detection", "❌", "❌", "✅ Auto-flagged per type"],
              ["Obligation Tracking", "⚠️ Spreadsheet", "✅ Basic", "✅ AI-powered alerts"],
              ["Audit Logs", "❌", "⚠️ Basic", "✅ Full trail (Enterprise)"],
              ["API Access", "❌", "⚠️ Limited", "✅ REST API (Enterprise)"],
              ["Setup Time", "Immediate", "3–6 weeks", "✅ Under 5 minutes"],
              ["Starting Price (India)", "₹0", "₹2L+/year", "✅ ₹7,999/month"],
            ].map(([cap, manual, clm, claustor], i) => (
              <div key={cap} style={{ display: "grid", gridTemplateColumns: "2.5fr 1fr 1.2fr 1.2fr",
                background: i % 2 === 0 ? C.surface : C.bg, borderTop: `1px solid ${C.border}` }}>
                <div style={{ padding: "13px 20px", fontSize: 13, fontWeight: 600, color: C.heading }}>{cap}</div>
                <div style={{ padding: "13px 20px", fontSize: 13, color: manual.includes("❌") ? C.error : C.muted }}>{manual}</div>
                <div style={{ padding: "13px 20px", fontSize: 13, color: clm.includes("❌") ? C.error : clm.includes("⚠️") ? C.warning : C.muted }}>{clm}</div>
                <div style={{ padding: "13px 20px", fontSize: 13, fontWeight: 700, color: C.success }}>{claustor}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── ENTERPRISE AI PLATFORM ─────────────────────────────── */}
      <section style={{ padding: "100px 5vw", background: "#070B19" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "#06B6D4", letterSpacing: "1.5px", textTransform: "uppercase" }}>Enterprise AI Platform</span>
            <h2 style={{ fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 900, color: "white", letterSpacing: "-1.5px", margin: "12px 0 16px" }}>
              Powered by Real AI Architecture
            </h2>
            <p style={{ fontSize: 17, color: "#475569", maxWidth: 560, margin: "0 auto", lineHeight: 1.6 }}>
              Not a wrapper. A purpose-built enterprise RAG system with hybrid retrieval, multi-model orchestration, and grounded answers.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24 }}>
            {/* Intelligence Engine */}
            <div style={{ background: "#0D152F", border: "1px solid #1E2D4A", borderRadius: 16, padding: 28 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#60A5FA", letterSpacing: "1px", marginBottom: 16, textTransform: "uppercase" }}>⚡ Intelligence Engine</div>
              {[
                ["Hybrid Search (BM25 + Vector + RRF)", "Keyword + semantic fusion with reciprocal rank reranking"],
                ["Multi-level Retrieval", "Parent → child → cross-reference chains"],
                ["Judge LLM Routing", "Groq → Haiku → Sonnet by complexity"],
                ["Groundedness Guard", "Citation-verified answers only"],
                ["Hallucination Detection", "Every response scored before delivery"],
                ["Multi-model Orchestration", "Best model selected per query type"],
              ].map(([title, desc]) => (
                <div key={title} style={{ display: "flex", gap: 10, marginBottom: 14, alignItems: "flex-start" }}>
                  <span style={{ color: "#0066FF", fontWeight: 700, fontSize: 14, marginTop: 1, flexShrink: 0 }}>✓</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "white" }}>{title}</div>
                    <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.5 }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Document Intelligence */}
            <div style={{ background: "#0D152F", border: "1px solid #1E2D4A", borderRadius: 16, padding: 28 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#A78BFA", letterSpacing: "1px", marginBottom: 16, textTransform: "uppercase" }}>📄 Document Intelligence</div>
              {[
                ["25 Clause Types", "Auto-extracted, risk-scored, playbook-matched"],
                ["Vision AI", "Scanned docs, images, payment tables via OCR"],
                ["Multilingual Support", "bge-m3 embeddings — search contracts in any language"],
                ["Hierarchical Chunking", "Article → clause → cross-reference aware"],
                ["Industry Risk Scoring", "Weighted by sector (pharma, banking, IT)"],
                ["Missing Clause Detection", "Flags absent protections automatically"],
              ].map(([title, desc]) => (
                <div key={title} style={{ display: "flex", gap: 10, marginBottom: 14, alignItems: "flex-start" }}>
                  <span style={{ color: "#A78BFA", fontWeight: 700, fontSize: 14, marginTop: 1, flexShrink: 0 }}>✓</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "white" }}>{title}</div>
                    <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.5 }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Global Compliance */}
            <div style={{ background: "#0D152F", border: "1px solid #1E2D4A", borderRadius: 16, padding: 28 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#06B6D4", letterSpacing: "1px", marginBottom: 16, textTransform: "uppercase" }}>�� Global Compliance</div>
              {[
                ["🇮🇳 India", "GSTIN · CIN · PAN · TAN · DIN"],
                ["🇬🇧 UK", "VAT (GB) · Company No · CRN"],
                ["🇺🇸 US", "EIN · DUNS · CAGE/SAM"],
                ["🇪🇺 EU", "VAT (DE/FR/NL/IT all prefixes)"],
                ["🇸🇬 Singapore", "UEN"],
                ["🇦🇺 Australia", "ABN · ACN"],
                ["🇦🇪 UAE", "TRN · Trade License"],
                ["🌐 Global", "IBAN · SWIFT · ISO Cert"],
              ].map(([flag, ids]) => (
                <div key={flag} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, padding: "7px 10px", background: "rgba(255,255,255,0.03)", borderRadius: 8 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "white" }}>{flag}</span>
                  <span style={{ fontSize: 11, color: "#475569" }}>{ids}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── ARCHITECTURE FLOW ───────────────────────────────────── */}
      <section style={{ padding: "80px 5vw", background: "#080C1A", borderTop: "1px solid #1E2D4A" }}>
        <div style={{ maxWidth: 960, margin: "0 auto", textAlign: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "#06B6D4", letterSpacing: "1.5px", textTransform: "uppercase" }}>Architecture</span>
          <h2 style={{ fontSize: "clamp(26px, 3.5vw, 40px)", fontWeight: 900, color: "white", letterSpacing: "-1px", margin: "12px 0 48px" }}>
            From Upload to Insight in Under 30 Seconds
          </h2>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexWrap: "wrap", gap: 0 }}>
            {[
              { icon: "📄", label: "Upload", sub: "Any format" },
              null,
              { icon: "🔍", label: "Parse + OCR", sub: "Vision AI" },
              null,
              { icon: "🧠", label: "Embed", sub: "bge-m3" },
              null,
              { icon: "⚖️", label: "Judge Routes", sub: "Groq LLM" },
              null,
              { icon: "🔎", label: "Hybrid Search", sub: "BM25 + Vector + RRF" },
              null,
              { icon: "✨", label: "Answer", sub: "Cited + Grounded" },
            ].map((step, i) =>
              step === null ? (
                <div key={i} style={{ color: "#1E3A5F", fontSize: 22, margin: "0 6px" }}>→</div>
              ) : (
                <div key={i} style={{ background: "#0D152F", border: "1px solid #1E2D4A", borderRadius: 12, padding: "14px 18px", textAlign: "center", minWidth: 90 }}>
                  <div style={{ fontSize: 26, marginBottom: 6 }}>{step.icon}</div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "white" }}>{step.label}</div>
                  <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>{step.sub}</div>
                </div>
              )
            )}
          </div>
        </div>
      </section>

      {/* ── ROADMAP ─────────────────────────────────────────────── */}
      <section style={{ padding: "80px 5vw", background: C.surface, borderTop: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 900, margin: "0 auto", textAlign: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: C.primary, letterSpacing: "1.5px", textTransform: "uppercase" }}>Roadmap</span>
          <h2 style={{ fontSize: "clamp(26px, 3.5vw, 40px)", fontWeight: 900, color: C.heading, letterSpacing: "-1px", margin: "12px 0 48px" }}>
            What's Coming Next
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
            {[
              { status: "✅ Live", label: "Contract Analysis", desc: "Upload, extract, risk-score 25 clause types", color: C.success },
              { status: "✅ Live", label: "AI Copilot", desc: "Natural language Q&A with citations", color: C.success },
              { status: "✅ Live", label: "Global Identifiers", desc: "8 countries, 25+ ID types auto-extracted", color: C.success },
              { status: "✅ Live", label: "AI Agents + Bulk Import", desc: "Celery pipeline, bulk ZIP processing", color: C.success },
              { status: "✅ Live", label: "Contract Comparison", desc: "Side-by-side clause-level comparison", color: C.success },
              { status: "✅ Live", label: "Workflow Automation", desc: "Obligation alerts, renewal tracking, bulk actions", color: C.success },
              { status: "✅ Live", label: "Multi-tenant SaaS", desc: "Auth0 SSO, per-org Pinecone namespace", color: C.success },
              { status: "🔜 Soon", label: "Enterprise MFA + Dedicated Pod", desc: "Auth0 MFA policy + per-org Pinecone pod", color: C.warning },
              { status: "🔮 V2", label: "Graph Intelligence", desc: "Entity relationship mapping across contracts", color: C.primary },
            ].map(({ status, label, desc, color }) => (
              <div key={label} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: 20, textAlign: "left" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color, marginBottom: 8 }}>{status}</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: C.heading, marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 12, color: C.muted }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SECURITY ────────────────────────────────────────────── */}
      <section id="security" style={{ padding: "80px 5vw", background: C.surface, borderTop: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 900, margin: "0 auto", textAlign: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: C.primary, letterSpacing: "1.5px", textTransform: "uppercase" }}>Security & Privacy</span>
          <h2 style={{ fontSize: "clamp(26px, 3.5vw, 40px)", fontWeight: 900, color: C.heading, letterSpacing: "-1px", margin: "12px 0 16px" }}>
            Enterprise Security by Design
          </h2>
          <p style={{ fontSize: 16, color: C.muted, marginBottom: 48, lineHeight: 1.6 }}>
            Your contracts are sensitive. We built Claustor with an 8-layer defence architecture from day one.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
            {[
              { icon: "🔐", title: "Encryption at Rest", desc: "AES-256 for all stored data" },
              { icon: "🔒", title: "Encryption in Transit", desc: "TLS 1.3 for all connections" },
              { icon: "👥", title: "Role-Based Access", desc: "Granular RBAC per user" },
              { icon: "📋", title: "Audit Logs", desc: "Full activity trail (Enterprise)" },
              { icon: "🌏", title: "Regional Deployment", desc: "Data stays in your region" },
              { icon: "🤖", title: "Private AI Option", desc: "Your data never trains models" },
            ].map(({ icon, title, desc }) => (
              <div key={title} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: 20, textAlign: "left" }}>
                <div style={{ fontSize: 24, marginBottom: 10 }}>{icon}</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: C.heading, marginBottom: 4 }}>{title}</div>
                <div style={{ fontSize: 12, color: C.muted }}>{desc}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 12, color: C.muted, marginTop: 20 }}>
            SOC 2 Ready architecture · GDPR compliant design · ISO 27001 aligned
          </p>
        </div>
      </section>

      {/* ── FAQ ─────────────────────────────────────────────────── */}
      <section style={{ padding: "80px 5vw", background: C.bg, borderTop: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 700, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: C.primary, letterSpacing: "1.5px", textTransform: "uppercase" }}>FAQ</span>
            <h2 style={{ fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: 900, color: C.heading, letterSpacing: "-1px", margin: "12px 0" }}>
              Common Questions
            </h2>
          </div>
          {[
            { q: "Is my contract data secure?", a: "Yes. All contracts are encrypted at rest (AES-256) and in transit (TLS 1.3). Your data never trains any AI model. Enterprise plans get dedicated data namespaces and regional deployment." },
            { q: "What file formats are supported?", a: "PDF, DOCX, XLS on Starter and above. Scanned PDFs and image-based contracts via Vision AI on Professional and Enterprise plans." },
            { q: "How long does analysis take?", a: "Most contracts are fully analysed in under 60 seconds. A 20-page contract typically takes 30-45 seconds including clause extraction, risk scoring, and vector indexing." },
            { q: "Can I use it for non-Indian contracts?", a: "Absolutely. Claustor supports contracts from 8 countries — India, UK, US, EU, Singapore, Australia, UAE, and global. Multi-language support covers Multilingual (bge-m3)." },
            { q: "What AI models power Claustor?", a: "We use a multi-model approach: Groq (llama-3.3-70b) for simple queries, Anthropic Haiku for medium complexity, and Anthropic Sonnet for complex legal analysis. Model selection is automatic based on query complexity." },
            { q: "Do you offer a free trial?", a: "Yes — the Free plan gives you 5 contracts and 100 AI queries at no cost, no credit card required. Starter and Professional plans include a 14-day trial." },
          ].map(({ q, a }, i) => (
            <FAQItem key={i} question={q} answer={a} />
          ))}
        </div>
      </section>

      {/* ── PRICING ─────────────────────────────────────────────── */}
      <section id="pricing" style={{ padding: "100px 5vw", background: C.bg }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: C.primary, letterSpacing: "1.5px", textTransform: "uppercase" }}>Pricing</span>
            <h2 style={{ fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 900, color: C.heading, letterSpacing: "-1.5px", margin: "12px 0 8px" }}>
              Simple, transparent pricing
            </h2>
            <p style={{ fontSize: 16, color: C.muted, marginBottom: 24 }}>Start free. Upgrade when you're ready. No hidden fees.</p>

            {/* Currency toggle */}
            <div style={{ display: "inline-flex", alignItems: "center", gap: 12, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: "6px 8px" }}>
              {(["INR", "USD"] as const).map(cur => (
                <button key={cur} onClick={() => setCurrency(cur)} style={{
                  padding: "6px 16px", borderRadius: 7, border: "none", cursor: "pointer",
                  fontWeight: 700, fontSize: 13,
                  background: currency === cur ? C.primary : "transparent",
                  color: currency === cur ? "white" : C.muted,
                  transition: "all 0.2s",
                }}>
                  {cur === "INR" ? "₹ INR" : "$ USD"}
                </button>
              ))}
              <button onClick={() => setShowIntl(true)} style={{
                padding: "6px 14px", borderRadius: 7, border: `1px dashed ${C.border}`, cursor: "pointer",
                fontWeight: 600, fontSize: 12, background: "transparent", color: C.muted,
              }}>
                🌍 Other currencies
              </button>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20 }}>
            {PLANS.map(plan => (
              <div key={plan.id} style={{
                background: plan.popular ? C.dark : C.surface,
                border: plan.popular ? `2px solid ${C.primary}` : `1px solid ${C.border}`,
                borderRadius: 16,
                padding: 28,
                position: "relative",
                transition: "transform 0.2s, box-shadow 0.2s",
              }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.transform = "translateY(-4px)"; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.transform = "none"; }}>

                {plan.popular && (
                  <div style={{ position: "absolute", top: -12, left: "50%", transform: "translateX(-50%)", background: C.primary, color: "white", fontSize: 11, fontWeight: 700, padding: "4px 14px", borderRadius: 20, whiteSpace: "nowrap" }}>
                    ⭐ Most Popular
                  </div>
                )}

                <div style={{ fontSize: 13, fontWeight: 700, color: plan.popular ? "#A5B4FC" : C.muted, marginBottom: 8 }}>{plan.tagline}</div>
                <div style={{ fontSize: 22, fontWeight: 900, color: plan.popular ? "white" : C.heading, marginBottom: 4 }}>{plan.name}</div>

                <div style={{ margin: "16px 0" }}>
                  {plan.custom ? (
                    <div style={{ fontSize: 28, fontWeight: 900, color: plan.popular ? "white" : C.heading }}>Custom</div>
                  ) : plan.priceINR === 0 ? (
                    <div style={{ fontSize: 32, fontWeight: 900, color: plan.popular ? "white" : C.heading }}>Free</div>
                  ) : (
                    <>
                      <span style={{ fontSize: 32, fontWeight: 900, color: plan.popular ? "white" : C.heading }}>{fmt(plan.priceINR)}</span>
                      <span style={{ fontSize: 14, color: plan.popular ? "#9CA3AF" : C.muted }}>/mo</span>
                    </>
                  )}
                </div>

                {/* Quick stats */}
                <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
                  {[
                    { label: "contracts", val: plan.contracts },
                    { label: "queries", val: plan.queries },
                    { label: "users", val: plan.users },
                  ].map(({ label, val }) => (
                    <div key={label} style={{ fontSize: 11, background: plan.popular ? "rgba(255,255,255,0.08)" : C.bg, color: plan.popular ? "#D1D5DB" : C.muted, padding: "3px 8px", borderRadius: 6, fontWeight: 500 }}>
                      {val} {label}
                    </div>
                  ))}
                </div>

                {/* Features */}
                <div style={{ marginBottom: 24 }}>
                  {plan.features.map(f => (
                    <div key={f} style={{ display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 8 }}>
                      <span style={{ color: plan.popular ? C.primary : C.success, fontWeight: 700, fontSize: 13, flexShrink: 0, marginTop: 1 }}>✓</span>
                      <span style={{ fontSize: 13, color: plan.popular ? "#D1D5DB" : C.body, lineHeight: 1.4 }}>{f}</span>
                    </div>
                  ))}
                </div>

                {plan.id === "enterprise" ? (
                  <button onClick={() => setShowEnterprise(true)} style={{
                    width: "100%", padding: "12px", border: `1px solid ${C.primary}`,
                    background: C.primaryLight, color: C.primary,
                    borderRadius: 10, fontWeight: 700, fontSize: 14, cursor: "pointer",
                  }}>
                    {plan.cta}
                  </button>
                ) : (
                  <Link href={plan.ctaLink} style={{
                    display: "block", textAlign: "center", padding: "12px",
                    background: plan.popular ? C.primary : plan.priceINR === 0 ? C.bg : C.primaryLight,
                    color: plan.popular ? "white" : plan.priceINR === 0 ? C.body : C.primary,
                    border: plan.popular ? "none" : `1px solid ${plan.priceINR === 0 ? C.border : C.primary}`,
                    borderRadius: 10, fontWeight: 700, fontSize: 14, textDecoration: "none",
                    boxShadow: plan.popular ? `0 4px 16px ${C.primaryGlow}` : "none",
                  }}>
                    {plan.cta}
                  </Link>
                )}
              </div>
            ))}
          </div>

          {/* Annual discount note */}
          <div style={{ textAlign: "center", marginTop: 24 }}>
            <span style={{ fontSize: 13, color: C.muted }}>
              💡 Save up to <strong style={{ color: C.primary }}>20%</strong> with annual billing · Industry packs available from {currency === "INR" ? "₹1,000" : "$12"}/mo
            </span>
          </div>

          {/* International note */}
          <div style={{ textAlign: "center", marginTop: 12 }}>
            <button onClick={() => setShowIntl(true)} style={{
              fontSize: 13, color: C.primary, background: "none", border: "none",
              cursor: "pointer", fontWeight: 600, textDecoration: "underline",
            }}>
              🌍 Outside India? Contact us for local currency pricing →
            </button>
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ────────────────────────────────────────────── */}
      <section style={{
        padding: "100px 5vw",
        background: `linear-gradient(135deg, ${C.dark} 0%, #1a1b35 100%)`,
        textAlign: "center",
      }}>
        <div style={{ maxWidth: 640, margin: "0 auto" }}>
          <h2 style={{ fontSize: "clamp(28px, 4vw, 48px)", fontWeight: 900, color: "white", letterSpacing: "-1.5px", margin: "0 0 16px" }}>
            Ready to transform your contract workflow?
          </h2>
          <p style={{ fontSize: 17, color: "#9CA3AF", lineHeight: 1.7, marginBottom: 36 }}>
            Join legal teams already using Claustor to review faster, catch risks earlier, and never miss a deadline.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/register" style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              background: C.primary, color: "white", fontWeight: 700, fontSize: 16,
              padding: "16px 32px", borderRadius: 10, textDecoration: "none",
              boxShadow: `0 8px 32px ${C.primaryGlow}`,
            }}>
              Start Free — No credit card →
            </Link>
            <button onClick={() => setShowEnterprise(true)} style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              background: "rgba(255,255,255,0.08)", color: "white", fontWeight: 600, fontSize: 16,
              padding: "16px 32px", borderRadius: 10, cursor: "pointer",
              border: "1px solid rgba(255,255,255,0.15)",
            }}>
              Talk to Sales
            </button>
          </div>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────── */}
      <footer style={{ background: C.dark, borderTop: `1px solid ${C.darkBorder}`, padding: "40px 5vw" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Logo height={36} />
            <span style={{ fontSize: 12, color: "#4B5563", marginLeft: 8 }}>© 2026 DKU Technologies Pvt. Ltd.</span>
          </div>
          <div style={{ display: "flex", gap: 24 }}>
            {["Privacy", "Terms", "Security", "Contact"].map(item => (
              <a key={item} href={`/${item.toLowerCase()}`} style={{ fontSize: 13, color: "#6B7280", textDecoration: "none" }}>{item}</a>
            ))}
          </div>
          <div style={{ fontSize: 12, color: "#374151" }}>
            Powered by Anthropic Claude · Groq · Pinecone
          </div>
        </div>
      </footer>

      {/* ── INTL POPUP ───────────────────────────────────────────── */}
      {showIntl && <IntlPopup onClose={() => setShowIntl(false)} />}
      {showDemo && <DemoPopup onClose={() => setShowDemo(false)} />}
      {showEnterprise && <EnterprisePopup onClose={() => setShowEnterprise(false)} />}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; }
      `}</style>
    </div>
  );
}
