"use client";
import { useEffect, useState } from "react";
import { users as usersAPI, getToken } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  success:"#22C55E", error:"#EF4444", warning:"#F59E0B",
};

const ROLES = [
  { value:"business_viewer",  label:"Business Viewer" },
  { value:"legal_reviewer",   label:"Legal Reviewer" },
  { value:"contract_manager", label:"Contract Manager" },
  { value:"dept_admin",       label:"Department Admin" },
  { value:"super_admin",      label:"Super Admin" },
];

const ROLE_COLORS: Record<string,string> = {
  super_admin:"#5B4BFF", dept_admin:"#8B5CF6",
  contract_manager:"#F59E0B", legal_reviewer:"#22C55E",
  business_viewer:"#6B7280",
};

export default function UsersPage() {
  const { user: currentUser } = useAuthStore();
  const isAdmin = ["super_admin","dept_admin"].includes(currentUser?.role || "");

  const [data, setData]               = useState<any>(null);
  const [loading, setLoading]         = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName]   = useState("");
  const [inviteRole, setInviteRole]   = useState("business_viewer");
  const [inviting, setInviting]       = useState(false);
  const [msg, setMsg]                 = useState("");
  const [editingId, setEditingId]     = useState<string|null>(null);
  const [newRole, setNewRole]         = useState("");
  const [busy, setBusy]               = useState<string|null>(null);

  const load = () => {
    setLoading(true);
    usersAPI.list().then(setData).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const showMsg = (m: string) => { setMsg(m); setTimeout(() => setMsg(""), 5000); };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviting(true);
    try {
      const result = await usersAPI.invite({ email:inviteEmail, full_name:inviteName, role:inviteRole });
      const link = result?.invite_url || "";
      showMsg(link ? `✅ Invited! Link: ${link}` : `✅ Invitation sent to ${inviteEmail}`);
      setInviteEmail(""); setInviteName("");
      load();
    } catch(e:any) { showMsg(`❌ ${e.message}`); }
    finally { setInviting(false); }
  };

  const changeRole = async (userId: string, role: string) => {
    setBusy(`role-${userId}`);
    try {
      const r = await fetch(`${API}/api/v1/users/${userId}/role`, {
        method:"PATCH",
        headers:{ Authorization:`Bearer ${getToken()}`, "Content-Type":"application/json" },
        body:JSON.stringify({ role }),
      });
      if (!r.ok) throw new Error((await r.json()).detail);
      showMsg(`✅ Role updated`);
      setEditingId(null);
      load();
    } catch(e:any) { showMsg(`❌ ${e.message}`); }
    finally { setBusy(null); }
  };

  const toggleActive = async (userId: string, active: boolean) => {
    setBusy(`active-${userId}`);
    try {
      const r = await fetch(`${API}/api/v1/users/${userId}/${active ? "deactivate" : "activate"}`, {
        method:"POST", headers:{ Authorization:`Bearer ${getToken()}` },
      });
      if (!r.ok) throw new Error((await r.json()).detail);
      showMsg(`✅ User ${active ? "deactivated" : "activated"}`);
      load();
    } catch(e:any) { showMsg(`❌ ${e.message}`); }
    finally { setBusy(null); }
  };

  const deleteUser = async (userId: string, email: string) => {
    if (!confirm(`Delete ${email}? This cannot be undone.`)) return;
    setBusy(`del-${userId}`);
    try {
      const r = await fetch(`${API}/api/v1/users/${userId}`, {
        method:"DELETE", headers:{ Authorization:`Bearer ${getToken()}` },
      });
      if (!r.ok && r.status !== 204) throw new Error((await r.json()).detail);
      showMsg(`✅ ${email} deleted`);
      load();
    } catch(e:any) { showMsg(`❌ ${e.message}`); }
    finally { setBusy(null); }
  };

  const ActionButtons = ({ u }: { u: any }) => {
    if (!isAdmin) return <span style={{fontSize:12,color:C.muted}}>—</span>;
    return (
      <div style={{display:"flex",gap:6}}>
        {editingId === u.id ? (
          <>
            <select value={newRole} onChange={e => setNewRole(e.target.value)}
              style={{fontSize:12,padding:"3px 8px",borderRadius:6,
                border:`1px solid ${C.primary}`,color:C.body}}>
              {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
            <button onClick={() => changeRole(u.id, newRole)}
              disabled={busy === `role-${u.id}`}
              style={{padding:"3px 10px",background:C.primary,color:"white",
                border:"none",borderRadius:6,fontSize:11,cursor:"pointer"}}>
              {busy === `role-${u.id}` ? "..." : "Save"}
            </button>
            <button onClick={() => setEditingId(null)}
              style={{padding:"3px 8px",background:"#F3F4F6",border:"none",
                borderRadius:6,cursor:"pointer",fontSize:11,color:C.muted}}>✕</button>
          </>
        ) : (
          <>
            <button onClick={() => { setEditingId(u.id); setNewRole(u.role); }}
              style={{padding:"4px 10px",fontSize:11,fontWeight:600,
                background:C.primaryLight,color:C.primary,
                border:`1px solid ${C.primary}30`,borderRadius:6,cursor:"pointer"}}>
              ✏️ Role
            </button>
            <button onClick={() => toggleActive(u.id, u.is_active)}
              disabled={busy === `active-${u.id}`}
              style={{padding:"4px 10px",fontSize:11,fontWeight:600,
                background:u.is_active?"#FFFBEB":"#F0FDF4",
                color:u.is_active?C.warning:C.success,
                border:`1px solid ${u.is_active?C.warning:C.success}30`,
                borderRadius:6,cursor:"pointer"}}>
              {busy === `active-${u.id}` ? "..." : u.is_active ? "⏸ Disable" : "▶ Enable"}
            </button>
            <button onClick={() => deleteUser(u.id, u.email)}
              disabled={busy === `del-${u.id}`}
              style={{padding:"4px 10px",fontSize:11,fontWeight:600,
                background:"#FEF2F2",color:C.error,
                border:`1px solid ${C.error}30`,borderRadius:6,cursor:"pointer"}}>
              {busy === `del-${u.id}` ? "..." : "🗑 Delete"}
            </button>
          </>
        )}
      </div>
    );
  };

  return (
    <div style={{padding:"32px 36px",maxWidth:1100}}>
      <div style={{marginBottom:24}}>
        <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Users</h1>
        <p style={{fontSize:14,color:C.muted}}>
          {data?.seats?.used}/{data?.seats?.max} seats · {data?.seats?.plan} plan
        </p>
      </div>

      {msg && (
        <div style={{padding:"10px 16px",borderRadius:8,marginBottom:16,
          background:msg.startsWith("✅")?"#F0FDF4":"#FEF2F2",
          color:msg.startsWith("✅")?C.success:C.error,fontSize:13,
          display:"flex",justifyContent:"space-between"}}>
          <span>{msg}</span>
          <button onClick={() => setMsg("")}
            style={{background:"none",border:"none",cursor:"pointer",fontSize:16,color:"inherit"}}>×</button>
        </div>
      )}

      <div style={{display:"grid",gridTemplateColumns:"1fr 360px",gap:24}}>

        {/* Users Table */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:12,overflow:"hidden"}}>
          {loading ? (
            <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading...</div>
          ) : (
            <table style={{width:"100%",borderCollapse:"collapse"}}>
              <thead>
                <tr style={{borderBottom:`1px solid ${C.border}`,background:C.bg}}>
                  {["User","Role","Status","Joined","Actions"].map(h => (
                    <th key={h} style={{padding:"10px 16px",textAlign:"left",
                      fontSize:11,fontWeight:700,color:C.muted,textTransform:"uppercase"}}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data?.users || []).map((u: any) => (
                  <tr key={u.id} style={{borderBottom:`1px solid ${C.border}`}}>
                    <td style={{padding:"12px 16px"}}>
                      <div style={{fontSize:14,fontWeight:600,color:C.heading}}>
                        {u.full_name || "—"}
                      </div>
                      <div style={{fontSize:12,color:C.muted}}>{u.email}</div>
                    </td>
                    <td style={{padding:"12px 16px"}}>
                      <span style={{fontSize:12,fontWeight:600,padding:"3px 10px",
                        borderRadius:20,
                        background:`${ROLE_COLORS[u.role]||C.muted}18`,
                        color:ROLE_COLORS[u.role]||C.muted}}>
                        {(u.role||"").replace(/_/g," ")}
                      </span>
                    </td>
                    <td style={{padding:"12px 16px"}}>
                      <span style={{fontSize:11,fontWeight:600,padding:"2px 8px",
                        borderRadius:20,
                        background:u.is_active?"#F0FDF4":"#F3F4F6",
                        color:u.is_active?"#16A34A":C.muted}}>
                        {u.is_active?"Active":"Inactive"}
                      </span>
                    </td>
                    <td style={{padding:"12px 16px",fontSize:12,color:C.muted}}>
                      {new Date(u.created_at).toLocaleDateString("en-IN",
                        {day:"2-digit",month:"short",year:"numeric"})}
                    </td>
                    <td style={{padding:"12px 16px"}}>
                      <ActionButtons u={u} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Invite Panel */}
        <div style={{background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:12,padding:24,alignSelf:"start"}}>
          <h2 style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:16}}>
            Invite user
          </h2>
          {!isAdmin && (
            <div style={{padding:"10px 12px",background:"#FEF2F2",borderRadius:8,
              fontSize:13,color:C.error,marginBottom:12}}>
              ⛔ Admin access required
            </div>
          )}
          <form onSubmit={handleInvite} style={{display:"flex",flexDirection:"column",gap:12}}>
            {[
              {label:"Full name",value:inviteName,set:setInviteName,type:"text",placeholder:"John Smith"},
              {label:"Email",value:inviteEmail,set:setInviteEmail,type:"email",placeholder:"john@company.com"},
            ].map(f => (
              <div key={f.label}>
                <label style={{display:"block",fontSize:13,fontWeight:600,
                  color:C.body,marginBottom:4}}>{f.label}</label>
                <input type={f.type} value={f.value}
                  onChange={e => f.set(e.target.value)}
                  placeholder={f.placeholder} required
                  style={{width:"100%",padding:"8px 12px",
                    border:`1.5px solid ${C.border}`,borderRadius:8,
                    fontSize:13,color:C.body,boxSizing:"border-box"}} />
              </div>
            ))}
            <div>
              <label style={{display:"block",fontSize:13,fontWeight:600,
                color:C.body,marginBottom:4}}>Role</label>
              <select value={inviteRole} onChange={e => setInviteRole(e.target.value)}
                style={{width:"100%",padding:"8px 12px",
                  border:`1.5px solid ${C.border}`,borderRadius:8,
                  fontSize:13,color:C.body}}>
                {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
            <button type="submit" disabled={inviting || !isAdmin}
              style={{padding:"10px",background:isAdmin?C.primary:"#9CA3AF",
                color:"white",border:"none",borderRadius:8,fontSize:14,
                fontWeight:600,cursor:inviting||!isAdmin?"not-allowed":"pointer"}}>
              {inviting?"Sending...":"Send invitation"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
