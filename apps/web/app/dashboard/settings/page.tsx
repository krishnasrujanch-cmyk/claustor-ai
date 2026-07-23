"use client";
import { useAuthStore } from "@/store/auth";

const C = { primary:"#5B4BFF", heading:"#111827", body:"#374151", muted:"#6B7280", border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC" };

export default function SettingsPage() {
  const { user, logout } = useAuthStore();
  return (
    <div style={{ padding:"32px 36px", maxWidth:700 }}>
      <h1 style={{ fontSize:24, fontWeight:800, color:C.heading, marginBottom:4 }}>Settings</h1>
      <p style={{ fontSize:14, color:C.muted, marginBottom:32 }}>Manage your account preferences</p>

      <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24, marginBottom:16 }}>
        <h2 style={{ fontSize:16, fontWeight:700, color:C.heading, marginBottom:16 }}>Account</h2>
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {[
            { label:"Email", value:user?.email },
            { label:"Role",  value:user?.role },
            { label:"Plan",  value:user?.plan },
            { label:"Org ID", value:user?.org_id },
          ].map(item => (
            <div key={item.label} style={{ display:"flex", justifyContent:"space-between", padding:"10px 0", borderBottom:`1px solid ${C.border}` }}>
              <span style={{ fontSize:14, color:C.muted }}>{item.label}</span>
              <span style={{ fontSize:14, fontWeight:600, color:C.body }}>{item.value}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
        <h2 style={{ fontSize:16, fontWeight:700, color:C.heading, marginBottom:16 }}>Danger zone</h2>
        <button onClick={logout} style={{ padding:"10px 20px", background:"#FEF2F2", border:"1px solid #FEE2E2", borderRadius:8, color:"#DC2626", fontSize:14, fontWeight:600, cursor:"pointer" }}>
          Sign out of all devices
        </button>
      </div>
    </div>
  );
}
