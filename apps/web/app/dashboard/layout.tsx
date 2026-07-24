"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

const C = {
  primary: "#5B4BFF", primaryLight: "#EEF0FF",
  heading: "#111827", body: "#374151", muted: "#6B7280",
  border: "#E5E7EB", surface: "#FFFFFF", bg: "#FAFBFC",
  sidebar: "#1C1B2E", sidebarText: "rgba(255,255,255,0.7)",
  sidebarActive: "rgba(91,75,255,0.25)",
};

// Permission → nav item mapping
const NAV_ITEMS = [
  { href:"/dashboard",             icon:"◻",  label:"Overview",      permission: null },
  { href:"/dashboard/contracts",   icon:"📄", label:"Contracts",     permission:"contracts:view" },
  { href:"/dashboard/copilot",     icon:"🤖", label:"AI Copilot",    permission:"chat:use" },
  { href:"/dashboard/reviews",     icon:"✅", label:"Reviews",       permission:"reviews:view" },
  { href:"/dashboard/compare",     icon:"⇄",  label:"Compare",       permission:"contracts:view" },
  { href:"/dashboard/playbook",    icon:"📚", label:"Playbook",      permission:"playbook:view" },
  { href:"/dashboard/obligations", icon:"📅", label:"Obligations",   permission:"obligations:view" },
  { href:"/dashboard/analytics",   icon:"📊", label:"Analytics",     permission:"analytics:view" },
  { href:"/dashboard/bulk",        icon:"📦", label:"Bulk Import",   permission:"bulk:import" },
];

const ADMIN_NAV = [
  { href:"/dashboard/admin/users",  icon:"👥", label:"Users",         permission:"users:view" },
  { href:"/dashboard/admin/roles",  icon:"🔑", label:"Roles",         permission:"users:manage" },
  { href:"/dashboard/admin/billing",icon:"💳", label:"Billing",       permission:"billing:view" },
  { href:"/dashboard/settings",     icon:"⚙️", label:"Settings",      permission:"settings:manage" },
];

// Role → permissions map (mirrors backend)
const ROLE_PERMISSIONS: Record<string, string[]> = {
  super_admin:      ["*"],
  dept_admin:       ["contracts:view","contracts:upload","contracts:delete","contracts:reprocess","chat:use","reviews:assign","reviews:view","analytics:view","analytics:export","users:view","users:invite","obligations:view","obligations:complete","playbook:view","playbook:manage","bulk:import","settings:manage","billing:view"],
  contract_manager: ["contracts:view","contracts:upload","contracts:delete","contracts:reprocess","chat:use","reviews:assign","reviews:view","analytics:view","obligations:view","obligations:complete","playbook:view","bulk:import"],
  legal_reviewer:   ["contracts:view","chat:use","reviews:view","reviews:decide","analytics:view","obligations:view","playbook:view"],
  business_viewer:  ["contracts:view","chat:use","analytics:view","obligations:view"],
};

function hasPermission(role: string, permission: string | null): boolean {
  if (!permission) return true;
  const perms = ROLE_PERMISSIONS[role] || [];
  return perms.includes("*") || perms.includes(permission);
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router   = useRouter();
  const { user, token, loadUser, logout } = useAuthStore();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const init = async () => {
      if (!token) { router.push("/login"); return; }
      if (!user) await loadUser();
      setChecked(true);
    };
    init();
  }, []);

  useEffect(() => {
    if (checked && !user && !token) router.push("/login");
  }, [checked, user, token]);

  if (!checked || !user) {
    return (
      <div style={{height:"100vh",display:"flex",alignItems:"center",justifyContent:"center",background:C.bg}}>
        <div style={{textAlign:"center"}}>
          <div style={{width:40,height:40,borderRadius:"50%",border:`3px solid ${C.primary}`,borderTopColor:"transparent",animation:"spin 0.8s linear infinite",margin:"0 auto 16px"}}/>
          <p style={{color:C.muted,fontSize:14}}>Loading...</p>
        </div>
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    );
  }

  const isActive = (href: string) => href === "/dashboard" ? pathname === href : pathname.startsWith(href);
  const isAdmin  = ["super_admin","dept_admin"].includes(user.role);

  const planBadgeColor: Record<string,string> = {
    free:"#6B7280", starter:"#3B82F6", professional:"#5B4BFF", enterprise:"#F59E0B",
  };

  // Filter nav based on role permissions
  const visibleNav = NAV_ITEMS.filter(item => hasPermission(user.role, item.permission));
  const visibleAdmin = ADMIN_NAV.filter(item => hasPermission(user.role, item.permission));

  return (
    <div style={{display:"flex",height:"100vh",overflow:"hidden"}}>
      {/* Sidebar */}
      <aside style={{width:240,background:C.sidebar,display:"flex",flexDirection:"column",flexShrink:0,overflowY:"auto"}}>
        {/* Logo + bells */}
        <div style={{padding:"16px",borderBottom:"1px solid rgba(255,255,255,0.08)"}}>
          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between"}}>
            <Link href="/dashboard" style={{textDecoration:"none",display:"flex",alignItems:"center",gap:8}}>
              <div style={{width:32,height:32,borderRadius:8,background:C.primary,display:"flex",alignItems:"center",justifyContent:"center",color:"white",fontWeight:700,fontSize:16}}>C</div>
              <span style={{color:"white",fontWeight:700,fontSize:16}}>Claustor</span>
            </Link>
            <div style={{display:"flex",gap:6}}>
              <NotificationBell />
              <ThemeToggle />
            </div>
          </div>
        </div>

        {/* Main nav */}
        <nav style={{padding:"12px 8px",flex:1}}>
          <div style={{fontSize:10,fontWeight:700,color:"rgba(255,255,255,0.3)",padding:"8px 12px 4px",letterSpacing:"0.08em",textTransform:"uppercase"}}>Main</div>
          {visibleNav.map(item=>(
            <Link key={item.href} href={item.href} style={{
              display:"flex",alignItems:"center",gap:10,padding:"9px 12px",borderRadius:8,
              textDecoration:"none",fontSize:14,marginBottom:2,
              fontWeight:isActive(item.href)?600:400,
              color:isActive(item.href)?"white":C.sidebarText,
              background:isActive(item.href)?C.sidebarActive:"transparent",
            }}>
              <span style={{fontSize:16}}>{item.icon}</span>{item.label}
            </Link>
          ))}

          {/* Admin nav */}
          {visibleAdmin.length > 0 && (
            <>
              <div style={{fontSize:10,fontWeight:700,color:"rgba(255,255,255,0.3)",padding:"16px 12px 4px",letterSpacing:"0.08em",textTransform:"uppercase"}}>Admin</div>
              {visibleAdmin.map(item=>(
                <Link key={item.href} href={item.href} style={{
                  display:"flex",alignItems:"center",gap:10,padding:"9px 12px",borderRadius:8,
                  textDecoration:"none",fontSize:14,marginBottom:2,
                  fontWeight:isActive(item.href)?600:400,
                  color:isActive(item.href)?"white":C.sidebarText,
                  background:isActive(item.href)?C.sidebarActive:"transparent",
                }}>
                  <span style={{fontSize:16}}>{item.icon}</span>{item.label}
                </Link>
              ))}
            </>
          )}
        </nav>

        {/* User section */}
        <div style={{padding:"12px 16px",borderTop:"1px solid rgba(255,255,255,0.08)"}}>
          <div style={{fontSize:11,fontWeight:700,color:planBadgeColor[user.plan]||"#6B7280",background:`${planBadgeColor[user.plan]||"#6B7280"}20`,padding:"3px 8px",borderRadius:6,display:"inline-block",marginBottom:10,textTransform:"uppercase",letterSpacing:"0.05em"}}>
            {user.plan}
          </div>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <div style={{width:32,height:32,borderRadius:"50%",background:C.primary,display:"flex",alignItems:"center",justifyContent:"center",color:"white",fontWeight:700,fontSize:13,flexShrink:0}}>
              {user.email.charAt(0).toUpperCase()}
            </div>
            <div style={{flex:1,minWidth:0}}>
              <div style={{color:"white",fontSize:13,fontWeight:600,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{user.email}</div>
              <div style={{color:C.sidebarText,fontSize:11}}>{user.role.replace(/_/g," ")}</div>
            </div>
          </div>
          <button onClick={logout} style={{width:"100%",marginTop:10,padding:"7px 12px",background:"rgba(255,255,255,0.06)",border:"none",borderRadius:6,color:C.sidebarText,fontSize:13,cursor:"pointer",textAlign:"left"}}>
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={{flex:1,overflowY:"auto",background:C.bg}}>
        {children}
      </main>
    </div>
  );
}
