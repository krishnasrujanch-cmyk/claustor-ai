"use client";

import Link from "next/link";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth";

const C = {
  primary: "#5B4BFF",
  primaryLight: "#EEF0FF",
  heading: "#111827",
  body: "#374151",
  muted: "#6B7280",
  border: "#E5E7EB",
  surface: "#FFFFFF",
  bg: "#FAFBFC",
  sidebar: "#1C1B2E",
  sidebarText: "rgba(255,255,255,0.7)",
  sidebarActive: "rgba(91,75,255,0.25)",
};

const NAV = [
  { href: "/dashboard",             icon: "◻",  label: "Overview" },
  { href: "/dashboard/contracts",   icon: "📄", label: "Contracts" },
  { href: "/dashboard/copilot",     icon: "🤖", label: "AI Copilot" },
  { href: "/dashboard/reviews",     icon: "✅", label: "Reviews" },
  { href: "/dashboard/compare",     icon: "⇄",  label: "Compare" },
  { href: "/dashboard/playbook",    icon: "📚", label: "Playbook" },
  { href: "/dashboard/obligations", icon: "📅", label: "Obligations" },
  { href: "/dashboard/analytics",   icon: "📊", label: "Analytics" },
  { href: "/dashboard/bulk",        icon: "📦", label: "Bulk Import" },
];

const ADMIN_NAV = [
  { href: "/dashboard/admin/users",   icon: "👥", label: "Users" },
  { href: "/dashboard/admin/billing", icon: "💳", label: "Billing" },
  { href: "/dashboard/settings",      icon: "⚙️", label: "Settings" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loadUser, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!user) {
      loadUser().catch(() => router.push("/login"));
    }
  }, [user, loadUser, router]);

  if (!user) {
    return (
      <div
        style={{
          height: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: C.bg,
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              border: `3px solid ${C.primary}`,
              borderTopColor: "transparent",
              animation: "spin 0.8s linear infinite",
              margin: "0 auto 16px",
            }}
          />
          <p style={{ color: C.muted, fontSize: 14 }}>Loading...</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const isActive = (href: string) =>
    href === "/dashboard" ? pathname === href : pathname.startsWith(href);

  const planBadgeColor: Record<string, string> = {
    free: "#6B7280",
    starter: "#3B82F6",
    professional: "#5B4BFF",
    enterprise: "#F59E0B",
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* Sidebar */}
      <aside
        style={{
          width: 240,
          background: C.sidebar,
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
          overflowY: "auto",
        }}
      >
        {/* Logo */}
        <div
          style={{
            padding: "20px 16px",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", width:"100%" }}>
          <Link
            href="/dashboard"
            style={{
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
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
            <span style={{ color: "white", fontWeight: 700, fontSize: 16 }}>
              Claustor
            </span>
          </Link>
          <NotificationBell />
          </div>
        </div>

        {/* Main nav */}
        <nav style={{ padding: "12px 8px", flex: 1 }}>
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "rgba(255,255,255,0.3)",
              padding: "8px 12px 4px",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Main
          </div>
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "9px 12px",
                borderRadius: 8,
                textDecoration: "none",
                fontSize: 14,
                fontWeight: isActive(item.href) ? 600 : 400,
                color: isActive(item.href) ? "white" : C.sidebarText,
                background: isActive(item.href) ? C.sidebarActive : "transparent",
                marginBottom: 2,
                transition: "background 0.1s",
              }}
            >
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              {item.label}
            </Link>
          ))}

          {/* Admin nav */}
          {user.role === "super_admin" && (
            <>
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: "rgba(255,255,255,0.3)",
                  padding: "16px 12px 4px",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                Admin
              </div>
              {ADMIN_NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "9px 12px",
                    borderRadius: 8,
                    textDecoration: "none",
                    fontSize: 14,
                    fontWeight: isActive(item.href) ? 600 : 400,
                    color: isActive(item.href) ? "white" : C.sidebarText,
                    background: isActive(item.href) ? C.sidebarActive : "transparent",
                    marginBottom: 2,
                  }}
                >
                  <span style={{ fontSize: 16 }}>{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </>
          )}
        </nav>

        {/* User section */}
        <div
          style={{
            padding: "12px 16px",
            borderTop: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {/* Plan badge */}
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: planBadgeColor[user.plan] || "#6B7280",
              background: `${planBadgeColor[user.plan]}20` || "#6B728020",
              padding: "3px 8px",
              borderRadius: 6,
              display: "inline-block",
              marginBottom: 10,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {user.plan}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: C.primary,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontWeight: 700,
                fontSize: 13,
                flexShrink: 0,
              }}
            >
              {user.email.charAt(0).toUpperCase()}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  color: "white",
                  fontSize: 13,
                  fontWeight: 600,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {user.email}
              </div>
              <div style={{ color: C.sidebarText, fontSize: 11 }}>{user.role}</div>
            </div>
          </div>

          <button
            onClick={logout}
            style={{
              width: "100%",
              marginTop: 10,
              padding: "7px 12px",
              background: "rgba(255,255,255,0.06)",
              border: "none",
              borderRadius: 6,
              color: C.sidebarText,
              fontSize: 13,
              cursor: "pointer",
              textAlign: "left",
            }}
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main
        style={{
          flex: 1,
          overflowY: "auto",
          background: C.bg,
        }}
      >
        {children}
      </main>
    </div>
  );
}
