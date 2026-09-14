"use client";
export const dynamic = "force-dynamic";
import { Nav, Footer, PageHero } from "@/components/nav-footer";

const C = {
  primary: "#0066FF",
  heading: "#111827",
  body: "#374151",
  muted: "#6B7280",
  border: "#E5E7EB",
  surface: "#FFFFFF",
  bg: "#FAFBFC",
  success: "#22C55E",
  warning: "#F59E0B",
  purple: "#7C3AED",
  teal: "#14B8A6",
};

const features = [
  {
    icon: "🔍",
    title: "Three-Mode AI Analysis",
    desc: "From 10-second factual lookups to comprehensive 80-second risk assessments. The system classifies your query complexity and applies the right depth automatically.",
  },
  {
    icon: "🏭",
    title: "15 Industry Playbooks",
    desc: "Risk scoring calibrated for finance, pharma, technology, manufacturing, energy, real estate, and more. The same clause gets different risk weight depending on your industry.",
  },
  {
    icon: "��️",
    title: "Regulatory Compliance",
    desc: "Scans contracts against DPDP Act, RBI Outsourcing, SEBI, GDPR, and HIPAA. Shows exactly which required clauses are missing and their severity.",
  },
  {
    icon: "🔔",
    title: "Real-Time Alerts",
    desc: "Automated email alerts for contract renewals, payment deadlines, and obligation due dates. Never miss a critical deadline again.",
  },
  {
    icon: "🧠",
    title: "Four-Layer Memory",
    desc: "Semantic cache for instant repeat answers, episodic memory for cross-session context, user preference tracking, and entity memory across contracts.",
  },
  {
    icon: "📊",
    title: "Cross-Contract Intelligence",
    desc: "Ask questions across your entire portfolio — expiring contracts, total exposure, vendor comparison — all from one search.",
  },
];

const stats = [
  { value: "30s", label: "Average analysis time" },
  { value: "15", label: "Industry playbooks" },
  { value: "5", label: "Regulatory frameworks" },
  { value: "1842x", label: "Cache speedup" },
];

const techStack = [
  { name: "Cohere", role: "Embeddings (1024-dim)" },
  { name: "Pinecone", role: "Vector search" },
  { name: "Claude", role: "Answer generation" },
  { name: "GPT-4o", role: "Fact extraction" },
  { name: "Cloud Run", role: "API infrastructure" },
  { name: "PostgreSQL", role: "Contract storage" },
];

export default function AboutPage() {
  return (
    <div style={{ background: C.bg, minHeight: "100vh" }}>
      <Nav />
      <PageHero
        badge="About Claustor"
        title="Enterprise AI, Built for Real Contracts"
        subtitle="We built Claustor because enterprises deserve better than keyword search and manual review."
      />

      {/* Mission Section */}
      <section style={{ maxWidth: 900, margin: "0 auto", padding: "60px 24px" }}>
        <h2 style={{ fontSize: 28, fontWeight: 800, color: C.heading, marginBottom: 16, textAlign: "center" }}>
          Why We Built Claustor
        </h2>
        <p style={{ fontSize: 16, lineHeight: 1.8, color: C.body, textAlign: "center", maxWidth: 700, margin: "0 auto 24px" }}>
          Enterprises manage hundreds of contracts across vendors, partners, and clients. 
          Reviewing each one takes hours. Risks get missed. Deadlines slip through. 
          Compliance gaps go unnoticed until it is too late.
        </p>
        <p style={{ fontSize: 16, lineHeight: 1.8, color: C.body, textAlign: "center", maxWidth: 700, margin: "0 auto" }}>
          Claustor changes that. Upload any contract and get instant AI-powered analysis — risks, 
          obligations, payment terms, compliance gaps, and renewal alerts. All grounded in the 
          actual contract text with clause-level citations.
        </p>
      </section>

      {/* Stats */}
      <section style={{ background: C.heading, padding: "48px 24px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", justifyContent: "space-around", flexWrap: "wrap", gap: 24 }}>
          {stats.map((s, i) => (
            <div key={i} style={{ textAlign: "center", minWidth: 140 }}>
              <div style={{ fontSize: 36, fontWeight: 800, color: C.primary }}>{s.value}</div>
              <div style={{ fontSize: 13, color: "#94A3B8", marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section style={{ maxWidth: 1000, margin: "0 auto", padding: "60px 24px" }}>
        <h2 style={{ fontSize: 28, fontWeight: 800, color: C.heading, marginBottom: 8, textAlign: "center" }}>
          What Makes Claustor Different
        </h2>
        <p style={{ fontSize: 15, color: C.muted, textAlign: "center", marginBottom: 40 }}>
          Not another chatbot. A contract intelligence platform built with enterprise DNA.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 24 }}>
          {features.map((f, i) => (
            <div key={i} style={{
              background: C.surface, borderRadius: 14, padding: 28,
              border: `1px solid ${C.border}`, transition: "box-shadow 0.2s",
            }}>
              <div style={{ fontSize: 28, marginBottom: 12 }}>{f.icon}</div>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: C.heading, marginBottom: 8 }}>{f.title}</h3>
              <p style={{ fontSize: 13, lineHeight: 1.7, color: C.body, margin: 0 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section style={{ background: C.surface, padding: "60px 24px", borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <h2 style={{ fontSize: 28, fontWeight: 800, color: C.heading, marginBottom: 8, textAlign: "center" }}>
            How Claustor Works
          </h2>
          <p style={{ fontSize: 15, color: C.muted, textAlign: "center", marginBottom: 40 }}>
            Three steps. Thirty seconds. Complete intelligence.
          </p>
          {[
            { step: "1", title: "Upload", desc: "Drop any contract — MSA, NDA, licensing agreement, vendor contract, employment agreement. PDF, DOCX, or scanned document." },
            { step: "2", title: "Analyze", desc: "Claustor's three-mode AI engine classifies complexity, extracts structured facts, and scores risks using industry-specific playbooks." },
            { step: "3", title: "Act", desc: "Get answers with clause citations, compliance gap analysis, obligation alerts, and cross-contract portfolio insights." },
          ].map((s, i) => (
            <div key={i} style={{ display: "flex", gap: 20, marginBottom: 32, alignItems: "flex-start" }}>
              <div style={{
                width: 44, height: 44, borderRadius: "50%", background: C.primary,
                color: "white", display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18, fontWeight: 800, flexShrink: 0,
              }}>{s.step}</div>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: C.heading, marginBottom: 4 }}>{s.title}</h3>
                <p style={{ fontSize: 14, lineHeight: 1.7, color: C.body, margin: 0 }}>{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section style={{ maxWidth: 900, margin: "0 auto", padding: "60px 24px" }}>
        <h2 style={{ fontSize: 28, fontWeight: 800, color: C.heading, marginBottom: 8, textAlign: "center" }}>
          Built With Enterprise-Grade Technology
        </h2>
        <p style={{ fontSize: 15, color: C.muted, textAlign: "center", marginBottom: 40 }}>
          Every component chosen for accuracy, speed, and reliability.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center" }}>
          {techStack.map((t, i) => (
            <div key={i} style={{
              padding: "12px 20px", borderRadius: 10, background: C.surface,
              border: `1px solid ${C.border}`, fontSize: 13, color: C.body,
            }}>
              <span style={{ fontWeight: 700, color: C.heading }}>{t.name}</span>
              <span style={{ color: C.muted }}> — {t.role}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Company */}
      <section style={{ background: C.heading, padding: "60px 24px", color: "white" }}>
        <div style={{ maxWidth: 700, margin: "0 auto", textAlign: "center" }}>
          <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 16 }}>DKU Technologies</h2>
          <p style={{ fontSize: 15, lineHeight: 1.8, color: "#CBD5E1", marginBottom: 24 }}>
            Claustor AI is built by DKU Technologies, an enterprise technology company 
            headquartered in Hyderabad, India. With 13+ years of experience building systems 
            for Apple, DHL, and OpenText, we bring enterprise architecture depth to every 
            contract Claustor reads.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.8, color: "#CBD5E1", marginBottom: 32 }}>
            We serve legal, procurement, finance, and compliance teams across financial services, 
            pharma, technology, manufacturing, energy, and real estate.
          </p>
          <a href="/contact" style={{
            display: "inline-block", padding: "14px 32px", borderRadius: 10,
            background: C.primary, color: "white", textDecoration: "none",
            fontWeight: 700, fontSize: 15,
          }}>
            Get in Touch
          </a>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: "60px 24px", textAlign: "center" }}>
        <h2 style={{ fontSize: 28, fontWeight: 800, color: C.heading, marginBottom: 12 }}>
          Ready to Transform Your Contract Review?
        </h2>
        <p style={{ fontSize: 15, color: C.muted, marginBottom: 28 }}>
          Free trial — no credit card required. Upload your first contract in 30 seconds.
        </p>
        <a href="/login?signup=true" style={{
          display: "inline-block", padding: "14px 36px", borderRadius: 10,
          background: C.primary, color: "white", textDecoration: "none",
          fontWeight: 700, fontSize: 15, boxShadow: "0 4px 16px rgba(0,102,255,0.25)",
        }}>
          Start Free Trial
        </a>
      </section>

      <Footer />
    </div>
  );
}
