"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuthStore } from "@/store/auth";
import { contracts as contractsAPI, billing as billingAPI, Contract } from "@/lib/api";

const C = {
  primary: "#5B4BFF",
  primaryLight: "#EEF0FF",
  heading: "#111827",
  body: "#374151",
  muted: "#6B7280",
  border: "#E5E7EB",
  surface: "#FFFFFF",
  bg: "#FAFBFC",
  success: "#22C55E",
  warning: "#F59E0B",
  error: "#EF4444",
};

function StatCard({
  label,
  value,
  sub,
  color = C.primary,
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div
      style={{
        background: C.surface,
        border: `1px solid ${C.border}`,
        borderRadius: 12,
        padding: "20px 24px",
      }}
    >
      <div style={{ fontSize: 13, color: C.muted, marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color, letterSpacing: "-0.02em" }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    high:   { bg: "#FEF2F2", text: "#DC2626" },
    medium: { bg: "#FFFBEB", text: "#D97706" },
    low:    { bg: "#F0FDF4", text: "#16A34A" },
  };
  const c = colors[level] || colors.low;
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 700,
        padding: "2px 8px",
        borderRadius: 20,
        background: c.bg,
        color: c.text,
        textTransform: "uppercase",
        letterSpacing: "0.04em",
      }}
    >
      {level}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    analyzed: { bg: "#F0FDF4", text: "#16A34A" },
    queued:   { bg: "#F5F3FF", text: "#7C3AED" },
    parsing:  { bg: "#EFF6FF", text: "#2563EB" },
    failed:   { bg: "#FEF2F2", text: "#DC2626" },
  };
  const c = colors[status] || { bg: "#F3F4F6", text: "#6B7280" };
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 600,
        padding: "2px 8px",
        borderRadius: 20,
        background: c.bg,
        color: c.text,
      }}
    >
      {status}
    </span>
  );
}

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [recentContracts, setRecentContracts] = useState<Contract[]>([]);
  const [usage, setUsage] = useState<{
    contracts: { used: number; limit: number; pct: number };
    queries: { used: number; limit: number; pct: number };
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [contractsData, usageData] = await Promise.all([
          contractsAPI.list({ page: 1, page_size: 5 }),
          billingAPI.usage(),
        ]);
        setRecentContracts(contractsData.contracts);
        setUsage(usageData.usage);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const highRiskCount = recentContracts.filter((c) => c.risk_level === "high").length;
  const analyzedCount = recentContracts.filter((c) => c.status === "analyzed").length;

  return (
    <div style={{ padding: "32px 36px", maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: C.heading, marginBottom: 4 }}>
          Good {getTimeOfDay()}, {user?.email.split("@")[0]} 👋
        </h1>
        <p style={{ fontSize: 14, color: C.muted }}>
          Here's what's happening with your contracts.
        </p>
      </div>

      {/* Stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 16,
          marginBottom: 32,
        }}
      >
        <StatCard
          label="Contracts analysed"
          value={usage?.contracts.used ?? 0}
          sub={`of ${usage?.contracts.limit ?? 5} this month`}
          color={C.primary}
        />
        <StatCard
          label="AI queries used"
          value={usage?.queries.used ?? 0}
          sub={`of ${usage?.queries.limit ?? 100} this month`}
          color="#06B6D4"
        />
        <StatCard
          label="High-risk clauses"
          value={highRiskCount}
          sub="in recent contracts"
          color={C.error}
        />
        <StatCard
          label="Plan"
          value={user?.plan?.toUpperCase() ?? "FREE"}
          sub={
            user?.plan === "free"
              ? "Upgrade for more contracts"
              : "Active subscription"
          }
          color={C.primary}
        />
      </div>

      {/* Usage bar */}
      {usage && (
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 12,
            padding: "20px 24px",
            marginBottom: 32,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 16,
            }}
          >
            <span style={{ fontSize: 14, fontWeight: 600, color: C.heading }}>
              Monthly usage
            </span>
            <Link
              href="/dashboard/admin/billing"
              style={{ fontSize: 13, color: C.primary, textDecoration: "none" }}
            >
              Upgrade plan →
            </Link>
          </div>

          {[
            { label: "Contracts", pct: usage.contracts.pct, used: usage.contracts.used, limit: usage.contracts.limit },
            { label: "AI queries", pct: usage.queries.pct, used: usage.queries.used, limit: usage.queries.limit },
          ].map((item) => (
            <div key={item.label} style={{ marginBottom: 12 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 13,
                  marginBottom: 6,
                }}
              >
                <span style={{ color: C.body }}>{item.label}</span>
                <span style={{ color: C.muted }}>
                  {item.used} / {item.limit}
                </span>
              </div>
              <div
                style={{
                  height: 6,
                  background: C.border,
                  borderRadius: 3,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${Math.min(item.pct, 100)}%`,
                    background:
                      item.pct > 90
                        ? C.error
                        : item.pct > 70
                        ? C.warning
                        : C.primary,
                    borderRadius: 3,
                    transition: "width 0.5s ease",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recent contracts */}
      <div
        style={{
          background: C.surface,
          border: `1px solid ${C.border}`,
          borderRadius: 12,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "16px 24px",
            borderBottom: `1px solid ${C.border}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: 15, fontWeight: 700, color: C.heading }}>
            Recent contracts
          </span>
          <Link
            href="/dashboard/contracts"
            style={{ fontSize: 13, color: C.primary, textDecoration: "none" }}
          >
            View all →
          </Link>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: C.muted, fontSize: 14 }}>
            Loading...
          </div>
        ) : recentContracts.length === 0 ? (
          <div style={{ padding: 60, textAlign: "center" }}>
            <div style={{ fontSize: 40, marginBottom: 16 }}>📄</div>
            <p style={{ fontSize: 15, fontWeight: 600, color: C.heading, marginBottom: 8 }}>
              No contracts yet
            </p>
            <p style={{ fontSize: 14, color: C.muted, marginBottom: 24 }}>
              Upload your first contract to get started
            </p>
            <Link
              href="/dashboard/contracts"
              style={{
                display: "inline-block",
                background: C.primary,
                color: "white",
                textDecoration: "none",
                padding: "10px 20px",
                borderRadius: 8,
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Upload contract
            </Link>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                {["Title", "Counterparty", "Risk", "Status", "Date"].map(
                  (h) => (
                    <th
                      key={h}
                      style={{
                        padding: "10px 24px",
                        textAlign: "left",
                        fontSize: 12,
                        fontWeight: 600,
                        color: C.muted,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {recentContracts.map((contract) => (
                <tr
                  key={contract.id}
                  style={{ borderBottom: `1px solid ${C.border}` }}
                >
                  <td style={{ padding: "14px 24px" }}>
                    <Link
                      href={`/dashboard/contracts/${contract.id}`}
                      style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: C.heading,
                        textDecoration: "none",
                      }}
                    >
                      {contract.title}
                    </Link>
                    {contract.contract_type && (
                      <div style={{ fontSize: 12, color: C.muted, marginTop: 2 }}>
                        {contract.contract_type}
                      </div>
                    )}
                  </td>
                  <td
                    style={{ padding: "14px 24px", fontSize: 14, color: C.body }}
                  >
                    {contract.counterparty || "—"}
                  </td>
                  <td style={{ padding: "14px 24px" }}>
                    {contract.risk_level ? (
                      <RiskBadge level={contract.risk_level} />
                    ) : (
                      <span style={{ color: C.muted, fontSize: 14 }}>—</span>
                    )}
                  </td>
                  <td style={{ padding: "14px 24px" }}>
                    <StatusBadge status={contract.status} />
                  </td>
                  <td
                    style={{ padding: "14px 24px", fontSize: 13, color: C.muted }}
                  >
                    {new Date(contract.created_at).toLocaleDateString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Quick actions */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 16,
          marginTop: 24,
        }}
      >
        {[
          { href: "/dashboard/contracts", icon: "⬆️", label: "Upload contract", desc: "Analyse a new contract" },
          { href: "/dashboard/copilot", icon: "🤖", label: "Ask AI Copilot", desc: "Chat about your contracts" },
          { href: "/dashboard/obligations", icon: "📅", label: "View obligations", desc: "Upcoming deadlines" },
        ].map((action) => (
          <Link
            key={action.href}
            href={action.href}
            style={{
              display: "block",
              background: C.surface,
              border: `1px solid ${C.border}`,
              borderRadius: 12,
              padding: "20px 24px",
              textDecoration: "none",
              transition: "box-shadow 0.15s",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.boxShadow = `0 4px 12px ${C.primary}15`)
            }
            onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "none")}
          >
            <div style={{ fontSize: 24, marginBottom: 8 }}>{action.icon}</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.heading, marginBottom: 4 }}>
              {action.label}
            </div>
            <div style={{ fontSize: 13, color: C.muted }}>{action.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function getTimeOfDay() {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  return "evening";
}
