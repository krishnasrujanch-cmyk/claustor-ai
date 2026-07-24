"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  error:"#EF4444", success:"#22C55E", warning:"#F59E0B",
};

const BUILT_IN_COLORS: Record<string,string> = {
  super_admin:"#5B4BFF", dept_admin:"#7C3AED",
  contract_manager:"#2563EB", legal_reviewer:"#0891B2",
  business_viewer:"#16A34A",
};

export default function RolesPage() {
  const [roles, setRoles]           = useState<any[]>([]);
  const [permissions, setPerms]     = useState<any[]>([]);
  const [grouped, setGrouped]       = useState<any[]>([]);
  const [loading, setLoading]       = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing]       = useState<any>(null);
  const [form, setForm]             = useState({ label:"", description:"", permissions:[] as string[] });
  const [saving, setSaving]         = useState(false);
  const [msg, setMsg]               = useState("");

  const load = async () => {
    setLoading(true);
    const token = getToken();
    const h = { Authorization:`Bearer ${token}` };
    try {
      const [rolesR, permsR] = await Promise.all([
        fetch(`${API}/api/v1/roles/`, {headers:h}).then(r=>r.json()),
        fetch(`${API}/api/v1/roles/permissions`, {headers:h}).then(r=>r.json()),
      ]);
      setRoles(rolesR.roles||[]);
      setPerms(permsR.permissions||[]);
      setGrouped(permsR.grouped||[]);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const togglePerm = (perm: string) => {
    setForm(f => ({
      ...f,
      permissions: f.permissions.includes(perm)
        ? f.permissions.filter(p=>p!==perm)
        : [...f.permissions, perm]
    }));
  };

  const save = async () => {
    if (!form.label) return;
    setSaving(true); setMsg("");
    const token = getToken();
    try {
      const url = editing
        ? `${API}/api/v1/roles/${editing.id}`
        : `${API}/api/v1/roles/`;
      const method = editing ? "PATCH" : "POST";
      const r = await fetch(url, {
        method, headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
        body: JSON.stringify(form),
      });
      if (!r.ok) throw new Error((await r.json()).detail);
      setMsg(`✅ Role ${editing?"updated":"created"} successfully`);
      setShowCreate(false); setEditing(null);
      setForm({label:"",description:"",permissions:[]});
      load();
    } catch(e:any) { setMsg(`❌ ${e.message}`); }
    finally { setSaving(false); }
  };

  const deleteRole = async (id: string, label: string) => {
    if (!confirm(`Delete role "${label}"?`)) return;
    const token = getToken();
    await fetch(`${API}/api/v1/roles/${id}`, {
      method:"DELETE", headers:{Authorization:`Bearer ${token}`}
    });
    load();
  };

  const startEdit = (role: any) => {
    setEditing(role);
    setForm({label:role.label, description:role.description||"", permissions:role.permissions||[]});
    setShowCreate(true);
  };

  return (
    <div style={{padding:"32px 36px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:28}}>
        <div>
          <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Roles & Permissions</h1>
          <p style={{fontSize:14,color:C.muted}}>5 built-in roles + create custom roles for your organisation</p>
        </div>
        <button onClick={()=>{setShowCreate(true);setEditing(null);setForm({label:"",description:"",permissions:[]});}}
          style={{padding:"10px 20px",background:C.primary,color:"white",border:"none",borderRadius:8,fontSize:14,fontWeight:600,cursor:"pointer"}}>
          + Create custom role
        </button>
      </div>

      {msg && <div style={{padding:"10px 16px",borderRadius:8,marginBottom:16,background:msg.startsWith("✅")?"#F0FDF4":"#FEF2F2",color:msg.startsWith("✅")?C.success:C.error,fontSize:13}}>{msg}</div>}

      {/* Create / Edit form */}
      {showCreate && (
        <div style={{background:C.surface,border:`1.5px solid ${C.primary}`,borderRadius:12,padding:28,marginBottom:28}}>
          <h2 style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:20}}>
            {editing ? `Edit: ${editing.label}` : "Create custom role"}
          </h2>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:20}}>
            <div>
              <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Role name *</label>
              <input value={form.label} onChange={e=>setForm({...form,label:e.target.value})}
                placeholder="e.g. Finance Team"
                style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}/>
            </div>
            <div>
              <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Description</label>
              <input value={form.description} onChange={e=>setForm({...form,description:e.target.value})}
                placeholder="What can this role do?"
                style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}/>
            </div>
          </div>

          {/* Permission groups */}
          <div style={{marginBottom:20}}>
            <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:12}}>
              Permissions ({form.permissions.length} selected)
            </label>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))",gap:16}}>
              {grouped.map((group:any)=>(
                <div key={group.group} style={{background:C.bg,border:`1px solid ${C.border}`,borderRadius:10,padding:16}}>
                  <div style={{fontSize:12,fontWeight:700,color:C.muted,marginBottom:10,textTransform:"uppercase",letterSpacing:"0.05em"}}>
                    {group.group}
                  </div>
                  <div style={{display:"flex",flexDirection:"column",gap:8}}>
                    {group.permissions.map((p:any)=>(
                      <label key={p.id} style={{display:"flex",alignItems:"center",gap:8,cursor:"pointer"}}>
                        <input type="checkbox" checked={form.permissions.includes(p.id)}
                          onChange={()=>togglePerm(p.id)}
                          style={{width:14,height:14,accentColor:C.primary}}/>
                        <span style={{fontSize:13,color:C.body}}>{p.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{display:"flex",gap:10}}>
            <button onClick={()=>{setShowCreate(false);setEditing(null);}}
              style={{padding:"10px 20px",border:`1px solid ${C.border}`,borderRadius:8,background:"none",fontSize:14,cursor:"pointer"}}>
              Cancel
            </button>
            <button onClick={save} disabled={!form.label||saving}
              style={{padding:"10px 20px",border:"none",borderRadius:8,background:!form.label||saving?"#D1D5DB":C.primary,color:"white",fontSize:14,fontWeight:600,cursor:"pointer"}}>
              {saving?"Saving...":editing?"Update role":"Create role"}
            </button>
          </div>
        </div>
      )}

      {/* Roles list */}
      {loading ? <div style={{textAlign:"center",padding:60,color:C.muted}}>Loading...</div> : (
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          {roles.map(role=>(
            <div key={role.id} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:20}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
                <div style={{flex:1}}>
                  <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:6}}>
                    <div style={{
                      width:10,height:10,borderRadius:"50%",flexShrink:0,
                      background:role.is_built_in?(BUILT_IN_COLORS[role.id]||C.primary):C.warning,
                    }}/>
                    <span style={{fontSize:16,fontWeight:700,color:C.heading}}>{role.label}</span>
                    {role.is_built_in && (
                      <span style={{fontSize:10,fontWeight:700,padding:"2px 6px",borderRadius:10,background:C.primaryLight,color:C.primary}}>BUILT-IN</span>
                    )}
                  </div>
                  <p style={{fontSize:13,color:C.muted,marginBottom:12}}>{role.description}</p>

                  {/* Permissions */}
                  <div style={{display:"flex",flexWrap:"wrap",gap:6}}>
                    {role.permissions[0]==="*" ? (
                      <span style={{fontSize:11,padding:"2px 8px",borderRadius:20,background:"#F0FDF4",color:C.success,fontWeight:600}}>
                        ✓ All permissions
                      </span>
                    ) : (role.permissions||[]).slice(0,8).map((p:string)=>(
                      <span key={p} style={{fontSize:11,padding:"2px 8px",borderRadius:20,background:C.bg,border:`1px solid ${C.border}`,color:C.body}}>
                        {p}
                      </span>
                    ))}
                    {(role.permissions||[]).length > 8 && (
                      <span style={{fontSize:11,color:C.muted,padding:"2px 8px"}}>+{role.permissions.length-8} more</span>
                    )}
                  </div>
                </div>

                {/* Actions — only for custom roles */}
                {!role.is_built_in && (
                  <div style={{display:"flex",gap:8,marginLeft:16}}>
                    <button onClick={()=>startEdit(role)}
                      style={{padding:"6px 14px",border:`1px solid ${C.border}`,borderRadius:8,background:"none",fontSize:13,cursor:"pointer",color:C.body}}>
                      Edit
                    </button>
                    <button onClick={()=>deleteRole(role.id,role.label)}
                      style={{padding:"6px 14px",border:`1px solid #FEE2E2`,borderRadius:8,background:"none",fontSize:13,cursor:"pointer",color:C.error}}>
                      Delete
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
