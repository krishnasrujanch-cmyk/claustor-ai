"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getToken } from "@/lib/api";

const API = "http://localhost:8000";

export function NotificationBell() {
  const [open, setOpen]       = useState(false);
  const [alerts, setAlerts]   = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const load = async () => {
    setLoading(true);
    const token = getToken();
    if (!token) { setLoading(false); return; }
    try {
      const r = await fetch(`${API}/api/v1/alerts/upcoming?days=90`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (r.ok) setAlerts(await r.json());
    } catch(e) {}
    finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const totalCount  = (alerts?.obligations?.length || 0) + (alerts?.renewals?.length || 0);
  const urgentCount = alerts?.summary?.urgent || 0;

  return (
    <div ref={ref} style={{ position:"relative", flexShrink:0 }}>
      {/* Bell button */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position: "relative",
          background: "rgba(255,255,255,0.1)",
          border: "none",
          borderRadius: 8,
          width: 36, height: 36,
          display: "flex", alignItems: "center", justifyContent: "center",
          cursor: "pointer",
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 16 }}>🔔</span>
        {totalCount > 0 && (
          <span style={{
            position: "absolute", top: -4, right: -4,
            minWidth: 18, height: 18, borderRadius: 9,
            background: urgentCount > 0 ? "#EF4444" : "#F59E0B",
            color: "white", fontSize: 10, fontWeight: 700,
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: "0 4px",
          }}>
            {totalCount > 9 ? "9+" : totalCount}
          </span>
        )}
      </button>

      {/* Dropdown — rendered in fixed position to avoid sidebar overflow */}
      {open && (
        <div style={{
          position: "fixed",
          top: 60, left: 200,
          width: 320,
          background: "#FFFFFF",
          border: "1px solid #E5E7EB",
          borderRadius: 12,
          boxShadow: "0 8px 32px rgba(0,0,0,0.16)",
          zIndex: 9999,
          overflow: "hidden",
        }}>
          {/* Header */}
          <div style={{
            padding: "12px 16px",
            borderBottom: "1px solid #E5E7EB",
            display: "flex", justifyContent: "space-between", alignItems: "center",
            background: "#FAFBFC",
          }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: "#111827" }}>
              Notifications
            </span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {urgentCount > 0 && (
                <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 20, background: "#FEF2F2", color: "#DC2626" }}>
                  {urgentCount} urgent
                </span>
              )}
              <button onClick={() => setOpen(false)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#9CA3AF", fontSize: 18, lineHeight: 1 }}>
                ×
              </button>
            </div>
          </div>

          {/* Content */}
          {loading ? (
            <div style={{ padding: 24, textAlign: "center", color: "#6B7280", fontSize: 13 }}>
              Loading...
            </div>
          ) : totalCount === 0 ? (
            <div style={{ padding: 32, textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>✅</div>
              <p style={{ fontSize: 13, color: "#6B7280", margin: 0 }}>No upcoming alerts</p>
            </div>
          ) : (
            <div style={{ maxHeight: 360, overflowY: "auto" }}>
              {/* Renewals */}
              {alerts?.renewals?.map((r: any) => (
                <Link key={r.id} href={`/dashboard/contracts/${r.id}`}
                  onClick={() => setOpen(false)}
                  style={{
                    display: "block", padding: "12px 16px",
                    borderBottom: "1px solid #F3F4F6",
                    textDecoration: "none",
                    background: r.urgency === "urgent" ? "#FEF2F2" : "#FFFFFF",
                  }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: r.urgency === "urgent" ? "#DC2626" : "#D97706", marginBottom: 4 }}>
                    {r.urgency === "urgent" ? "🚨" : "⏰"} Contract renewal in {r.days_until_expiry} days
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#111827" }}>{r.title}</div>
                  {r.counterparty && <div style={{ fontSize: 11, color: "#6B7280", marginTop: 2 }}>{r.counterparty}</div>}
                </Link>
              ))}

              {/* Obligations */}
              {alerts?.obligations?.filter((o: any) => o.due_date).slice(0, 6).map((o: any) => (
                <Link key={o.id} href="/dashboard/obligations"
                  onClick={() => setOpen(false)}
                  style={{
                    display: "block", padding: "12px 16px",
                    borderBottom: "1px solid #F3F4F6",
                    textDecoration: "none",
                    background: o.urgency === "urgent" ? "#FFFBEB" : "#FFFFFF",
                  }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: o.urgency === "urgent" ? "#DC2626" : "#D97706", marginBottom: 4 }}>
                    {o.urgency === "urgent" ? "🚨" : "📅"} Due in {o.days_until_due} days
                    {o.amount && <span style={{ marginLeft: 8, color: "#6B7280" }}>{o.currency} {o.amount.toLocaleString()}</span>}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#111827" }}>{o.title}</div>
                  <div style={{ fontSize: 11, color: "#6B7280", marginTop: 2 }}>{o.type}</div>
                </Link>
              ))}
            </div>
          )}

          {/* Footer */}
          <div style={{ padding: "10px 16px", borderTop: "1px solid #E5E7EB", background: "#FAFBFC" }}>
            <Link href="/dashboard/obligations" onClick={() => setOpen(false)}
              style={{ fontSize: 13, color: "#5B4BFF", textDecoration: "none", fontWeight: 600 }}>
              View all obligations →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
