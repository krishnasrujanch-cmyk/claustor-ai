"use client";
import { API_URL as API } from "@/lib/config";

import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
import { X, User, Building2, Save, LogOut, ChevronRight } from "lucide-react";



interface ProfileData {
  user: { id: string; email: string; full_name: string; role: string };
  org: { id: string; name: string; gstin: string; address: string; phone: string; website: string; plan: string; industry: string };
}

export function ProfilePopup({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const { token, logout } = useAuthStore();
  const [tab, setTab] = useState<"profile" | "org">("profile");
  const [data, setData] = useState<ProfileData | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState<any>({});
  const popupRef = useRef<HTMLDivElement>(null);

  // Load profile
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => { setData(d); setForm({ ...d.user, ...d.org }); })
      .catch(() => {});
  }, [token]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) onClose();
    };
    setTimeout(() => document.addEventListener("mousedown", handler), 100);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  // Close on ESC
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const save = async () => {
    if (!token) return;
    setSaving(true);
    try {
      // Update user
      await fetch(`${API}/api/v1/users/me`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: form.full_name }),
      });
      // Update org
      await fetch(`${API}/api/v1/users/me/org`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name, gstin: form.gstin,
          address: form.address, phone: form.phone, website: form.website,
        }),
      });
      setSaved(true);
      // Reload data to reflect saved changes
      const res = await fetch(`${API}/api/v1/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const d = await res.json();
        setData(d);
        setForm({ ...d.user, ...d.org });
      }
      setTimeout(() => setSaved(false), 2000);
    } catch { /* ignore */ }
    finally { setSaving(false); }
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
    onClose();
  };

  const planColors: Record<string, string> = {
    free: "#6B7280", starter: "#3B82F6", professional: "#8B5CF6", enterprise: "#F59E0B",
  };

  const isAdmin = data?.user.role === "super_admin";

  return (
    <div
      ref={popupRef}
      style={{
        position: "fixed", top: 60, right: 16,
        width: 360, background: "white", borderRadius: 16,
        boxShadow: "0 20px 60px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05)",
        zIndex: 1000, overflow: "hidden",
        animation: "slideDown 0.15s ease",
      }}
    >
      {/* Header */}
      <div style={{
        padding: "16px 16px 12px",
        borderBottom: "1px solid #F1F5F9",
        background: "linear-gradient(135deg,#0A1628,#0F2040)",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* Avatar */}
            <div style={{
              width: 40, height: 40, borderRadius: "50%",
              background: "linear-gradient(135deg,#5B4BFF,#06B6D4)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 700, color: "white",
              boxShadow: "0 0 0 2px rgba(255,255,255,0.2)",
            }}>
              {data?.user.full_name?.charAt(0)?.toUpperCase() || data?.user.email?.charAt(0)?.toUpperCase() || "U"}
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "white" }}>
                {data?.user.full_name || data?.user.email || "Loading..."}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
                <span style={{ fontSize: 10, color: "rgba(255,255,255,0.5)" }}>
                  {data?.user.role}
                </span>
                <span style={{
                  fontSize: 9, fontWeight: 700, padding: "1px 6px", borderRadius: 20,
                  background: planColors[data?.org.plan || "free"] || "#6B7280",
                  color: "white", textTransform: "uppercase",
                }}>
                  {data?.org.plan || "free"}
                </span>
              </div>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "rgba(255,255,255,0.1)", border: "none",
            borderRadius: 8, width: 28, height: 28, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", color: "white",
          }}>
            <X size={13} />
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, marginTop: 12 }}>
          {[
            { key: "profile", label: "My Profile", icon: User },
            { key: "org", label: "Organisation", icon: Building2 },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key as any)}
              style={{
                flex: 1, padding: "6px 8px", borderRadius: 8, border: "none",
                cursor: "pointer", fontSize: 11, fontWeight: 600,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 5,
                background: tab === key ? "rgba(255,255,255,0.15)" : "transparent",
                color: tab === key ? "white" : "rgba(255,255,255,0.5)",
                transition: "all 0.15s",
              }}
            >
              <Icon size={12} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: "16px" }}>
        {tab === "profile" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Field label="Full Name" value={form.full_name || ""}
              onChange={v => setForm((f: any) => ({ ...f, full_name: v }))} />
            <Field label="Email" value={data?.user.email || ""} disabled />
            <Field label="Role" value={data?.user.role || ""} disabled />
          </div>
        )}

        {tab === "org" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Field label="Organisation Name" value={form.name || ""}
              onChange={isAdmin ? v => setForm((f: any) => ({ ...f, name: v })) : undefined}
              disabled={!isAdmin} />
            <Field label="GSTIN" value={form.gstin || ""}
              placeholder="22AAAAA0000A1Z5"
              onChange={isAdmin ? v => setForm((f: any) => ({ ...f, gstin: v })) : undefined}
              disabled={!isAdmin} />
            <Field label="Address" value={form.address || ""}
              placeholder="Street, City, State, PIN"
              onChange={isAdmin ? v => setForm((f: any) => ({ ...f, address: v })) : undefined}
              disabled={!isAdmin} multiline />
            <Field label="Phone" value={form.phone || ""}
              placeholder="+91 98765 43210"
              onChange={isAdmin ? v => setForm((f: any) => ({ ...f, phone: v })) : undefined}
              disabled={!isAdmin} />
            <Field label="Website" value={form.website || ""}
              placeholder="https://company.com"
              onChange={isAdmin ? v => setForm((f: any) => ({ ...f, website: v })) : undefined}
              disabled={!isAdmin} />
            {!isAdmin && (
              <div style={{ fontSize: 11, color: "#94A3B8", textAlign: "center" }}>
                Only admins can edit organisation details
              </div>
            )}
          </div>
        )}

        {/* Save button */}
        {(tab === "profile" || isAdmin) && (
          <button
            onClick={save}
            disabled={saving}
            style={{
              width: "100%", marginTop: 16, padding: "10px",
              borderRadius: 10, border: "none", cursor: saving ? "not-allowed" : "pointer",
              background: saved ? "#22C55E" : "#0066FF", color: "white",
              fontSize: 13, fontWeight: 700,
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              transition: "all 0.2s",
            }}
          >
            <Save size={13} />
            {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
          </button>
        )}
      </div>

      {/* Footer */}
      <div style={{
        padding: "10px 16px",
        borderTop: "1px solid #F1F5F9",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <button
          onClick={() => { router.push("/dashboard/settings"); onClose(); }}
          style={{
            fontSize: 12, color: "#64748B", background: "none",
            border: "none", cursor: "pointer", fontWeight: 500,
            display: "flex", alignItems: "center", gap: 4,
          }}
        >
          Settings <ChevronRight size={12} />
        </button>
        <button
          onClick={handleLogout}
          style={{
            fontSize: 12, color: "#EF4444", background: "#FEF2F2",
            border: "1px solid #FCA5A5", borderRadius: 8,
            padding: "5px 12px", cursor: "pointer", fontWeight: 600,
            display: "flex", alignItems: "center", gap: 4,
          }}
        >
          <LogOut size={12} />
          Sign Out
        </button>
      </div>

      <style>{`
        @keyframes slideDown { from { opacity:0; transform:translateY(-8px) } to { opacity:1; transform:translateY(0) } }
      `}</style>
    </div>
  );
}

function Field({
  label, value, onChange, disabled, placeholder, multiline,
}: {
  label: string; value: string;
  onChange?: (v: string) => void;
  disabled?: boolean; placeholder?: string; multiline?: boolean;
}) {
  const style: any = {
    width: "100%", padding: "7px 10px", borderRadius: 8,
    border: "1px solid #E2E8F0", fontSize: 12, color: "#111827",
    background: disabled ? "#F8FAFC" : "white",
    boxSizing: "border-box", outline: "none",
    resize: "none", fontFamily: "inherit",
  };
  return (
    <div>
      <label style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 4 }}>
        {label}
      </label>
      {multiline
        ? <textarea rows={2} value={value} onChange={e => onChange?.(e.target.value)}
            disabled={disabled} placeholder={placeholder} style={style} />
        : <input value={value} onChange={e => onChange?.(e.target.value)}
            disabled={disabled} placeholder={placeholder} style={style} />
      }
    </div>
  );
}
