"use client";
import { useEffect, useState } from "react";
import { users as usersAPI } from "@/lib/api";

const C = { primary:"#5B4BFF", heading:"#111827", body:"#374151", muted:"#6B7280", border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC" };

export default function UsersPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("business_viewer");
  const [inviting, setInviting] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () => usersAPI.list().then(setData).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviting(true); setMsg("");
    try {
      await usersAPI.invite({ email:inviteEmail, full_name:inviteName, role:inviteRole });
      setMsg(`✅ Invitation sent to ${inviteEmail}`);
      setInviteEmail(""); setInviteName("");
      load();
    } catch(err:any) { setMsg(`❌ ${err.message}`); }
    finally { setInviting(false); }
  };

  return (
    <div style={{ padding:"32px 36px" }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:32 }}>
        <div>
          <h1 style={{ fontSize:24, fontWeight:800, color:C.heading, marginBottom:4 }}>Users</h1>
          <p style={{ fontSize:14, color:C.muted }}>
            {data?.seats?.used}/{data?.seats?.max} seats used · {data?.seats?.plan} plan
          </p>
        </div>
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 360px", gap:24 }}>
        <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, overflow:"hidden" }}>
          {loading ? <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading...</div> : (
            <table style={{ width:"100%", borderCollapse:"collapse" }}>
              <thead><tr style={{ borderBottom:`1px solid ${C.border}` }}>
                {["User","Role","Status","Joined"].map(h=>(
                  <th key={h} style={{ padding:"10px 20px", textAlign:"left", fontSize:12, fontWeight:600, color:C.muted, textTransform:"uppercase" }}>{h}</th>
                ))}
              </tr></thead>
              <tbody>{data?.users?.map((u:any) => (
                <tr key={u.id} style={{ borderBottom:`1px solid ${C.border}` }}>
                  <td style={{ padding:"14px 20px" }}>
                    <div style={{ fontSize:14, fontWeight:600, color:C.heading }}>{u.full_name || u.email}</div>
                    <div style={{ fontSize:12, color:C.muted }}>{u.email}</div>
                  </td>
                  <td style={{ padding:"14px 20px", fontSize:13, color:C.body }}>{u.role}</td>
                  <td style={{ padding:"14px 20px" }}>
                    <span style={{ fontSize:11, fontWeight:600, padding:"2px 8px", borderRadius:20, background:u.is_active?"#F0FDF4":"#F3F4F6", color:u.is_active?"#16A34A":"#6B7280" }}>
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td style={{ padding:"14px 20px", fontSize:13, color:C.muted }}>
                    {new Date(u.created_at).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>

        <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
          <h2 style={{ fontSize:16, fontWeight:700, color:C.heading, marginBottom:16 }}>Invite user</h2>
          {msg && <div style={{ padding:"8px 12px", borderRadius:8, background:msg.startsWith("✅")?"#F0FDF4":"#FEF2F2", color:msg.startsWith("✅")?"#16A34A":"#DC2626", fontSize:13, marginBottom:16 }}>{msg}</div>}
          <form onSubmit={handleInvite} style={{ display:"flex", flexDirection:"column", gap:12 }}>
            {[
              { label:"Full name", value:inviteName, onChange:setInviteName, type:"text", placeholder:"John Smith" },
              { label:"Email", value:inviteEmail, onChange:setInviteEmail, type:"email", placeholder:"john@company.com" },
            ].map(f => (
              <div key={f.label}>
                <label style={{ display:"block", fontSize:13, fontWeight:600, color:C.body, marginBottom:4 }}>{f.label}</label>
                <input type={f.type} value={f.value} onChange={e=>f.onChange(e.target.value)} placeholder={f.placeholder} required
                  style={{ width:"100%", padding:"8px 12px", border:`1.5px solid ${C.border}`, borderRadius:8, fontSize:13, color:C.body }} />
              </div>
            ))}
            <div>
              <label style={{ display:"block", fontSize:13, fontWeight:600, color:C.body, marginBottom:4 }}>Role</label>
              <select value={inviteRole} onChange={e=>setInviteRole(e.target.value)}
                style={{ width:"100%", padding:"8px 12px", border:`1.5px solid ${C.border}`, borderRadius:8, fontSize:13, color:C.body }}>
                <option value="business_viewer">Business Viewer</option>
                <option value="legal_reviewer">Legal Reviewer</option>
                <option value="contract_manager">Contract Manager</option>
                <option value="dept_admin">Department Admin</option>
                <option value="super_admin">Super Admin</option>
              </select>
            </div>
            <button type="submit" disabled={inviting}
              style={{ padding:"10px", background:C.primary, color:"white", border:"none", borderRadius:8, fontSize:14, fontWeight:600, cursor:"pointer" }}>
              {inviting ? "Sending..." : "Send invitation"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
