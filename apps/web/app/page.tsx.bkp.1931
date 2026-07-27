"use client";

import Link from "next/link";
import { useState } from "react";

// ── Design tokens (inline for self-contained landing) ─
const C = {
  primary: "#5B4BFF",
  primaryHover: "#4C3FE0",
  primaryLight: "#EEF0FF",
  accent: "#06B6D4",
  heading: "#111827",
  body: "#374151",
  muted: "#6B7280",
  border: "#E5E7EB",
  surface: "#FFFFFF",
  bg: "#FAFBFC",
};

// ── Data ──────────────────────────────────────────────

const FEATURES = [
  {
    icon: "⚡",
    title: "Instant clause extraction",
    desc: "Upload any PDF or DOCX. AI extracts every clause with section references in under 60 seconds.",
  },
  {
    icon: "🔍",
    title: "Hybrid search",
    desc: "Ask anything in plain English. Semantic + keyword search finds exact figures, dates, and terms.",
  },
  {
    icon: "🎯",
    title: "Risk scoring",
    desc: "Every clause scored 0–100. High-risk clauses flagged instantly — liability caps, auto-renewals, broad indemnities.",
  },
  {
    icon: "📅",
    title: "Obligation tracking",
    desc: "Payment dates, renewal notices, audit rights. Never miss a deadline again.",
  },
  {
    icon: "🤖",
    title: "AI Copilot chat",
    desc: "Ask 'What is the liability cap?' and get a cited answer from the contract. Not a hallucination.",
  },
  {
    icon: "🔒",
    title: "Enterprise security",
    desc: "SOC 2 Type II. AES-256 encryption. Per-tenant data isolation. Your contracts stay yours.",
  },
];

const PLANS = [
  {
    name: "Free",
    price: "₹0",
    period: "",
    desc: "5 contracts. Forever.",
    features: ["5 contracts", "100 AI queries/month", "Basic extraction", "1 user"],
    cta: "Start free",
    href: "/login?signup=true",
    highlight: false,
  },
  {
    name: "Starter",
    price: "₹3,999",
    period: "/month",
    desc: "For growing legal teams.",
    features: [
      "100 contracts/month",
      "5,000 AI queries",
      "OCR + table extraction",
      "10 users",
      "Email alerts",
      "14-day free trial",
    ],
    cta: "Start trial",
    href: "/login?signup=true&plan=starter",
    highlight: false,
  },
  {
    name: "Professional",
    price: "₹16,499",
    period: "/month",
    desc: "For serious contract teams.",
    features: [
      "1,000 contracts/month",
      "50,000 AI queries",
      "Vision + handwriting",
      "50 users",
      "API access",
      "Webhooks",
      "Risk heatmap",
      "14-day free trial",
    ],
    cta: "Start trial",
    href: "/login?signup=true&plan=professional",
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    desc: "For large organisations.",
    features: [
      "Unlimited contracts",
      "Unlimited queries",
      "SSO / SAML",
      "SCIM provisioning",
      "Dedicated instance",
      "SLA guarantee",
      "Custom playbooks",
    ],
    cta: "Talk to us",
    href: "mailto:hello@claustor.com",
    highlight: false,
  },
];

const STATS = [
  { value: "< 60s", label: "Contract analysis time" },
  { value: "94%", label: "Clause extraction accuracy" },
  { value: "8×", label: "Faster than manual review" },
  { value: "₹0", label: "To get started" },
];

const FAQS = [
  {
    q: "What file types does Claustor support?",
    a: "PDF, DOCX, and DOC. We handle scanned PDFs via OCR on Starter plans and above.",
  },
  {
    q: "Is my contract data secure?",
    a: "Yes. Each organisation gets an isolated namespace in our vector store. Contracts are AES-256 encrypted at rest. We never use your data to train AI models.",
  },
  {
    q: "Does Claustor replace legal counsel?",
    a: "No — and we're clear about that. Claustor is a contract intelligence tool, not legal advice. It helps legal teams work faster, not replace them.",
  },
  {
    q: "Which LLMs does Claustor use?",
    a: "We use Groq (Llama 3.3 70b) as primary, with Gemini and OpenAI as fallbacks. You get the best available model automatically.",
  },
  {
    q: "Can I use Claustor via API?",
    a: "Yes. Professional plan and above includes API access with scoped keys (contracts:read, chat:write, etc).",
  },
];

// ── Components ────────────────────────────────────────

function Nav() {
  const [open, setOpen] = useState(false);
  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "rgba(255,255,255,0.95)",
        backdropFilter: "blur(8px)",
        borderBottom: `1px solid ${C.border}`,
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "0 24px",
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {/* Logo */}
        <Link href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: C.primary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
              fontWeight: 700,
              fontSize: 16,
            }}
          >
            C
          </div>
          <span style={{ fontWeight: 700, fontSize: 18, color: C.heading }}>Claustor</span>
        </Link>

        {/* Desktop nav */}
        <div style={{ display: "flex", alignItems: "center", gap: 32 }} className="hidden md:flex">
          {["Features", "Pricing", "Security", "Docs"].map((item) => (
            <Link
              key={item}
              href={`#${item.toLowerCase()}`}
              style={{ color: C.body, textDecoration: "none", fontSize: 14, fontWeight: 500 }}
            >
              {item}
            </Link>
          ))}
        </div>

        {/* CTA */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link
            href="/login"
            style={{
              color: C.body,
              textDecoration: "none",
              fontSize: 14,
              fontWeight: 500,
              padding: "8px 16px",
            }}
          >
            Sign in
          </Link>
          <Link
            href="/login?signup=true"
            style={{
              background: C.primary,
              color: "white",
              textDecoration: "none",
              fontSize: 14,
              fontWeight: 600,
              padding: "8px 20px",
              borderRadius: 8,
            }}
          >
            Start free
          </Link>
        </div>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <section
      style={{
        padding: "96px 24px 80px",
        textAlign: "center",
        background: `linear-gradient(180deg, ${C.primaryLight} 0%, ${C.bg} 100%)`,
      }}
    >
      <div style={{ maxWidth: 760, margin: "0 auto" }}>
        {/* Badge */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            background: C.primaryLight,
            border: `1px solid ${C.primary}30`,
            borderRadius: 20,
            padding: "4px 14px",
            fontSize: 13,
            fontWeight: 600,
            color: C.primary,
            marginBottom: 24,
          }}
        >
          <span>🤖</span> Powered by Groq · Llama 3.3 70b
        </div>

        {/* Headline */}
        <h1
          style={{
            fontSize: "clamp(36px, 6vw, 64px)",
            fontWeight: 800,
            color: C.heading,
            lineHeight: 1.15,
            letterSpacing: "-0.02em",
            marginBottom: 24,
          }}
        >
          Your contracts,{" "}
          <span style={{ color: C.primary }}>understood in seconds</span>
        </h1>

        {/* Subhead */}
        <p
          style={{
            fontSize: "clamp(16px, 2.5vw, 20px)",
            color: C.body,
            lineHeight: 1.6,
            marginBottom: 40,
            maxWidth: 560,
            margin: "0 auto 40px",
          }}
        >
          Upload any PDF or DOCX. Claustor extracts every clause, scores
          every risk, and answers any question — with citations from the
          actual contract.
        </p>

        {/* CTAs */}
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link
            href="/login?signup=true"
            style={{
              background: C.primary,
              color: "white",
              textDecoration: "none",
              fontSize: 16,
              fontWeight: 600,
              padding: "14px 28px",
              borderRadius: 10,
              boxShadow: `0 4px 14px ${C.primary}40`,
            }}
          >
            Start free — no card required
          </Link>
          <Link
            href="#demo"
            style={{
              background: C.surface,
              color: C.heading,
              textDecoration: "none",
              fontSize: 16,
              fontWeight: 600,
              padding: "14px 28px",
              borderRadius: 10,
              border: `1.5px solid ${C.border}`,
            }}
          >
            See how it works →
          </Link>
        </div>

        {/* Trust line */}
        <p style={{ marginTop: 24, fontSize: 13, color: C.muted }}>
          Free forever · No credit card · 5 contracts included
        </p>
      </div>
    </section>
  );
}

function Stats() {
  return (
    <section style={{ background: C.surface, borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}` }}>
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "48px 24px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 32,
          textAlign: "center",
        }}
      >
        {STATS.map((s) => (
          <div key={s.label}>
            <div style={{ fontSize: 36, fontWeight: 800, color: C.primary, letterSpacing: "-0.02em" }}>
              {s.value}
            </div>
            <div style={{ fontSize: 13, color: C.muted, marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Features() {
  return (
    <section id="features" style={{ padding: "96px 24px", background: C.bg }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 64 }}>
          <h2 style={{ fontSize: 36, fontWeight: 800, color: C.heading, marginBottom: 16 }}>
            Everything your legal team needs
          </h2>
          <p style={{ fontSize: 18, color: C.body, maxWidth: 520, margin: "0 auto" }}>
            From upload to insight in under 60 seconds.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: 24,
          }}
        >
          {FEATURES.map((f) => (
            <div
              key={f.title}
              style={{
                background: C.surface,
                border: `1px solid ${C.border}`,
                borderRadius: 16,
                padding: 28,
                transition: "box-shadow 0.15s ease",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.boxShadow = `0 4px 20px ${C.primary}15`)
              }
              onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "none")}
            >
              <div style={{ fontSize: 28, marginBottom: 12 }}>{f.icon}</div>
              <h3 style={{ fontSize: 17, fontWeight: 700, color: C.heading, marginBottom: 8 }}>
                {f.title}
              </h3>
              <p style={{ fontSize: 14, color: C.body, lineHeight: 1.6 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    { n: "1", title: "Upload contract", desc: "PDF or DOCX. Any language. Any size up to 50MB." },
    { n: "2", title: "AI analyses", desc: "Clauses extracted, risks scored, obligations identified — in under 60 seconds." },
    { n: "3", title: "Ask anything", desc: "\"What is the liability cap?\" → cited answer from the actual contract." },
    { n: "4", title: "Track & alert", desc: "Renewal notices, payment dates, audit rights. Never miss a deadline." },
  ];

  return (
    <section id="demo" style={{ padding: "96px 24px", background: C.surface }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 64 }}>
          <h2 style={{ fontSize: 36, fontWeight: 800, color: C.heading, marginBottom: 16 }}>
            How it works
          </h2>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {steps.map((step, i) => (
            <div
              key={step.n}
              style={{
                display: "flex",
                gap: 24,
                alignItems: "flex-start",
                paddingBottom: i < steps.length - 1 ? 40 : 0,
                position: "relative",
              }}
            >
              {/* Line */}
              {i < steps.length - 1 && (
                <div
                  style={{
                    position: "absolute",
                    left: 19,
                    top: 40,
                    bottom: 0,
                    width: 2,
                    background: C.border,
                  }}
                />
              )}
              {/* Number */}
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: "50%",
                  background: C.primary,
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: 16,
                  flexShrink: 0,
                  zIndex: 1,
                }}
              >
                {step.n}
              </div>
              <div style={{ paddingTop: 8 }}>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: C.heading, marginBottom: 4 }}>
                  {step.title}
                </h3>
                <p style={{ fontSize: 15, color: C.body, lineHeight: 1.6 }}>{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  return (
    <section id="pricing" style={{ padding: "96px 24px", background: C.bg }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 64 }}>
          <h2 style={{ fontSize: 36, fontWeight: 800, color: C.heading, marginBottom: 16 }}>
            Simple, transparent pricing
          </h2>
          <p style={{ fontSize: 18, color: C.body }}>
            Start free. Upgrade when you need more.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 20,
            alignItems: "start",
          }}
        >
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              style={{
                background: C.surface,
                border: plan.highlight ? `2px solid ${C.primary}` : `1px solid ${C.border}`,
                borderRadius: 16,
                padding: 28,
                position: "relative",
              }}
            >
              {plan.highlight && (
                <div
                  style={{
                    position: "absolute",
                    top: -12,
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: C.primary,
                    color: "white",
                    fontSize: 11,
                    fontWeight: 700,
                    padding: "3px 12px",
                    borderRadius: 20,
                    whiteSpace: "nowrap",
                  }}
                >
                  MOST POPULAR
                </div>
              )}

              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: C.muted, marginBottom: 4 }}>
                  {plan.name}
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                  <span style={{ fontSize: 32, fontWeight: 800, color: C.heading }}>
                    {plan.price}
                  </span>
                  <span style={{ fontSize: 14, color: C.muted }}>{plan.period}</span>
                </div>
                <p style={{ fontSize: 13, color: C.muted, marginTop: 4 }}>{plan.desc}</p>
              </div>

              <ul style={{ listStyle: "none", padding: 0, margin: "0 0 24px", display: "flex", flexDirection: "column", gap: 8 }}>
                {plan.features.map((f) => (
                  <li key={f} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: C.body }}>
                    <span style={{ color: C.primary, fontWeight: 700 }}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <Link
                href={plan.href}
                style={{
                  display: "block",
                  textAlign: "center",
                  background: plan.highlight ? C.primary : "transparent",
                  color: plan.highlight ? "white" : C.primary,
                  border: plan.highlight ? "none" : `1.5px solid ${C.primary}`,
                  textDecoration: "none",
                  fontSize: 14,
                  fontWeight: 600,
                  padding: "10px 20px",
                  borderRadius: 8,
                }}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FAQ() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section style={{ padding: "96px 24px", background: C.surface }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <h2 style={{ fontSize: 36, fontWeight: 800, color: C.heading, textAlign: "center", marginBottom: 48 }}>
          Frequently asked
        </h2>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {FAQS.map((faq, i) => (
            <div
              key={i}
              style={{
                border: `1px solid ${C.border}`,
                borderRadius: 12,
                overflow: "hidden",
              }}
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                style={{
                  width: "100%",
                  padding: "16px 20px",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  textAlign: "left",
                }}
              >
                <span style={{ fontSize: 15, fontWeight: 600, color: C.heading }}>
                  {faq.q}
                </span>
                <span style={{ color: C.primary, fontWeight: 700, fontSize: 18, flexShrink: 0 }}>
                  {open === i ? "−" : "+"}
                </span>
              </button>
              {open === i && (
                <div style={{ padding: "0 20px 16px", fontSize: 14, color: C.body, lineHeight: 1.6 }}>
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section
      style={{
        padding: "96px 24px",
        background: `linear-gradient(135deg, ${C.primary} 0%, #4338CA 100%)`,
        textAlign: "center",
      }}
    >
      <div style={{ maxWidth: 600, margin: "0 auto" }}>
        <h2 style={{ fontSize: 36, fontWeight: 800, color: "white", marginBottom: 16 }}>
          Start understanding your contracts today
        </h2>
        <p style={{ fontSize: 18, color: "rgba(255,255,255,0.85)", marginBottom: 40 }}>
          Free forever. No credit card. 5 contracts included.
        </p>
        <Link
          href="/login?signup=true"
          style={{
            display: "inline-block",
            background: "white",
            color: C.primary,
            textDecoration: "none",
            fontSize: 16,
            fontWeight: 700,
            padding: "14px 32px",
            borderRadius: 10,
          }}
        >
          Get started free →
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer
      style={{
        background: C.heading,
        color: "rgba(255,255,255,0.6)",
        padding: "48px 24px",
        textAlign: "center",
      }}
    >
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ marginBottom: 24, display: "flex", justifyContent: "center", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: C.primary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            C
          </div>
          <span style={{ color: "white", fontWeight: 700, fontSize: 16 }}>Claustor</span>
        </div>
        <div style={{ display: "flex", justifyContent: "center", gap: 32, marginBottom: 24, flexWrap: "wrap" }}>
          {["Privacy", "Terms", "Security", "Blog", "Docs", "Contact"].map((item) => (
            <Link
              key={item}
              href={`/${item.toLowerCase()}`}
              style={{ color: "rgba(255,255,255,0.6)", textDecoration: "none", fontSize: 14 }}
            >
              {item}
            </Link>
          ))}
        </div>
        <p style={{ fontSize: 13 }}>
          © 2026 Claustor AI · claustor.com · Built by DKU Technologies
        </p>
      </div>
    </footer>
  );
}

// ── Page ──────────────────────────────────────────────

export default function LandingPage() {
  return (
    <main>
      <Nav />
      <Hero />
      <Stats />
      <Features />
      <HowItWorks />
      <Pricing />
      <FAQ />
      <CTA />
      <Footer />
    </main>
  );
}
