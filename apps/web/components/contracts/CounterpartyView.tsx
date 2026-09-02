"use client";
import { useState } from "react";
import Link from "next/link";
import { C } from "@/lib/design-tokens";

const RISK_META: Record<string, { bg: string; text: string; dot: string }> = {
  critical: { bg: "#FEF2F2", text: "#991B1B", dot: "#DC2626" },
  high:     { bg: "#FEF2F2", text: "#DC2626", dot: "#EF4444" },
  medium:   { bg: "#FFFBEB", text: "#D97706", dot: "#F59E0B" },
  low:      { bg: "#F0FDF4", text: "#16A34A", dot: "#22C55E" },
};

function RiskBadge({ level }: { level: string }) {
  const m = RISK_META[level] || { bg: "#F3F4F6", text: "#6B7280", dot: "#9CA3AF" };
  return (
    <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 20,
      background: m.bg, color: m.text, textTransform: "uppercase", letterSpacing: "0.04em" }}>
      {level}
    </span>
  );
}

function formatValue(v: number | null | undefined, currency?: string): string {
  if (!v) return "—";
  const sym = currency === "INR" ? "₹" : "$";
  if (v >= 10000000) return `${sym}${(v / 1000000).toFixed(1)}M`;
  if (v >= 100000)   return `${sym}${(v / 1000).toFixed(0)}K`;
  return `${sym}${v.toLocaleString()}`;
}

interface Contract {
  id: string;
  title: string;
  contract_type: string;
  status: string;
  risk_level: string;
  risk_score: number;
  contract_value: number | null;
  contract_currency: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  review_status: string | null;
  original_filename: string;
  created_at: string | null;
}

interface CounterpartyGroup {
  counterparty: string;
  contract_count: number;
  total_value: number;
  currency: string;
  max_risk_level: string;
  avg_risk_score: number;
  earliest_expiry: string | null;
  expiring_soon: number;
  contracts: Contract[];
}

interface Props {
  groups: CounterpartyGroup[];
  totalCounterparties: number;
  totalContracts: number;
  portfolioValue: number;
  loading: boolean;
}

export function CounterpartyView({ groups, totalCounterparties, totalContracts, portfolioValue, loading }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (name: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const expandAll = () => setExpanded(new Set(groups.map(g => g.counterparty)));
  const collapseAll = () => setExpanded(new Set());

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
        <div style={{ color: C.muted, fontSize: 14 }}>Loading counterparty groups...</div>
      </div>
    );
  }

  return (
    <div>
      {/* Summary bar */}
      <div style={{ display: "flex", gap: 24, marginBottom: 20, padding: "14px 20px",
        background: "#F8FAFC", borderRadius: 12, border: "1px solid #E2E8F0" }}>
        <div>
          <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>Counterparties</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: C.text }}>{totalCounterparties}</div>
        </div>
        <div style={{ borderLeft: "1px solid #E2E8F0", paddingLeft: 24 }}>
          <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>Total Contracts</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: C.text }}>{totalContracts}</div>
        </div>
        <div style={{ borderLeft: "1px solid #E2E8F0", paddingLeft: 24 }}>
          <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>Portfolio Value</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: C.text }}>{formatValue(portfolioValue)}</div>
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button onClick={expandAll} style={{ fontSize: 12, color: C.primary, background: "none",
            border: "none", cursor: "pointer", textDecoration: "underline" }}>Expand All</button>
          <span style={{ color: "#CBD5E1" }}>|</span>
          <button onClick={collapseAll} style={{ fontSize: 12, color: C.primary, background: "none",
            border: "none", cursor: "pointer", textDecoration: "underline" }}>Collapse All</button>
        </div>
      </div>

      {/* Groups */}
      {groups.length === 0 ? (
        <div style={{ textAlign: "center", padding: 60, color: C.muted }}>No contracts found</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {groups.map(group => {
            const isOpen = expanded.has(group.counterparty);
            const riskMeta = RISK_META[group.max_risk_level] || RISK_META.low;

            return (
              <div key={group.counterparty} style={{ border: "1px solid #E2E8F0", borderRadius: 12,
                overflow: "hidden", background: "#fff",
                borderLeft: `4px solid ${riskMeta.dot}` }}>

                {/* Group header */}
                <div onClick={() => toggle(group.counterparty)}
                  style={{ display: "flex", alignItems: "center", padding: "14px 20px",
                    cursor: "pointer", gap: 16, userSelect: "none",
                    background: isOpen ? "#F8FAFC" : "#fff",
                    transition: "background 0.15s" }}>

                  {/* Expand icon */}
                  <span style={{ fontSize: 14, color: C.muted, transition: "transform 0.2s",
                    transform: isOpen ? "rotate(90deg)" : "rotate(0deg)", width: 16, textAlign: "center" }}>
                    ▶
                  </span>

                  {/* Counterparty name */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 600, color: C.text,
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {group.counterparty}
                    </div>
                    <div style={{ fontSize: 12, color: C.muted, marginTop: 2 }}>
                      {group.contract_count} contract{group.contract_count !== 1 ? "s" : ""}
                      {group.expiring_soon > 0 && (
                        <span style={{ color: "#DC2626", fontWeight: 600, marginLeft: 8 }}>
                          ⚠ {group.expiring_soon} expiring soon
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Metrics */}
                  <div style={{ display: "flex", gap: 20, alignItems: "center", flexShrink: 0 }}>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: 11, color: C.muted }}>Value</div>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>
                        {formatValue(group.total_value, group.currency)}
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: 11, color: C.muted }}>Risk Score</div>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>{group.avg_risk_score}</div>
                    </div>
                    <RiskBadge level={group.max_risk_level || "low"} />
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: 11, color: C.muted }}>Earliest Expiry</div>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>
                        {group.earliest_expiry || "—"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Expanded contracts table */}
                {isOpen && (
                  <div style={{ borderTop: "1px solid #E2E8F0" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                      <thead>
                        <tr style={{ background: "#F8FAFC" }}>
                          <th style={{ padding: "8px 16px", textAlign: "left", fontWeight: 600,
                            color: C.muted, fontSize: 11, textTransform: "uppercase" }}>Contract</th>
                          <th style={{ padding: "8px 16px", textAlign: "left", fontWeight: 600,
                            color: C.muted, fontSize: 11, textTransform: "uppercase" }}>Type</th>
                          <th style={{ padding: "8px 16px", textAlign: "left", fontWeight: 600,
                            color: C.muted, fontSize: 11, textTransform: "uppercase" }}>Value</th>
                          <th style={{ padding: "8px 16px", textAlign: "left", fontWeight: 600,
                            color: C.muted, fontSize: 11, textTransform: "uppercase" }}>Risk</th>
                          <th style={{ padding: "8px 16px", textAlign: "left", fontWeight: 600,
                            color: C.muted, fontSize: 11, textTransform: "uppercase" }}>Expiry</th>
                          <th style={{ padding: "8px 16px", textAlign: "left", fontWeight: 600,
                            color: C.muted, fontSize: 11, textTransform: "uppercase" }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.contracts.map(c => (
                          <tr key={c.id} style={{ borderTop: "1px solid #F1F5F9" }}>
                            <td style={{ padding: "10px 16px" }}>
                              <Link href={`/dashboard/contracts/${c.id}`}
                                style={{ color: C.primary, textDecoration: "none", fontWeight: 500,
                                  fontSize: 13 }}>
                                {c.title}
                              </Link>
                            </td>
                            <td style={{ padding: "10px 16px", color: C.muted }}>{c.contract_type || "—"}</td>
                            <td style={{ padding: "10px 16px", fontWeight: 500 }}>
                              {formatValue(c.contract_value, c.contract_currency)}
                            </td>
                            <td style={{ padding: "10px 16px" }}>
                              <RiskBadge level={c.risk_level || "low"} />
                            </td>
                            <td style={{ padding: "10px 16px", color: C.muted }}>{c.expiry_date || "—"}</td>
                            <td style={{ padding: "10px 16px" }}>
                              <span style={{ fontSize: 11, fontWeight: 600, padding: "2px 8px",
                                borderRadius: 10, background: c.status === "analyzed" ? "#F0FDF4" : "#FEF3C7",
                                color: c.status === "analyzed" ? "#16A34A" : "#92400E" }}>
                                {c.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
