"use client";
import { API_URL as API } from "@/lib/config";
export const dynamic = "force-dynamic";
import { useEffect, useState, useRef, useMemo } from "react";
import { users as usersAPI, getToken } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Search, MoreVertical, UserPlus, Edit2, X, Check } from "lucide-react";


const C = {
  primary:"#0066FF", primaryLight:"#E6F0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  success:"#22C55E", error:"#EF4444", warning:"#F59E0B",
};

const ROLES = [
  {value:"business_viewer",  label:"Business Viewer"},
  {value:"legal_reviewer",   label:"Legal Reviewer"},
  {value:"contract_manager", label:"Contract Manager"},
  {value:"dept_admin",       label:"Dept Admin"},
  {value:"super_admin",      label:"Super Admin"},
];

const ROLE_STYLE: Record<string,{bg:string;text:string}> = {
  super_admin:      {bg:"#EEF2FF", text:"#4F46E5"},
  dept_admin:       {bg:"#F5F3FF", text:"#7C3AED"},
  contract_manager: {bg:"#FFFBEB", text:"#D97706"},
  legal_reviewer:   {bg:"#E0F2FE", text:"#0284C7"},
  business_viewer:  {bg:"#F1F5F9", text:"#64748B"},
};

// ── Relative time ─────────────────────────────────────────────────────────────
function relTime(dateStr?: string): string {
  if (!dateStr) return "Never";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff/60000);
  const hrs  = Math.floor(diff/3600000);
  const days = Math.floor(diff/86400000);
  if (mins < 1)   return "Just now";
  if (mins < 60)  return `${mins}m ago`;
  if (hrs < 24)   return `${hrs}h ago`;
  if (days < 7)   return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-IN",{day:"2-digit",month:"short"});
}

// ── Avatar ────────────────────────────────────────────────────────────────────
function Avatar({name,email}: {name?:string; email:string}) {
  const initials = name
    ? name.split(" ").map(w=>w[0]).join("").toUpperCase().slice(0,2)
    : email[0].toUpperCase();
  const colors = ["#0066FF","#8B5CF6","#EC4899","#F59E0B","#22C55E","#06B6D4"];
  const color  = colors[email.charCodeAt(0) % colors.length];
  return (
    <div style={{width:36,height:36,borderRadius:"50%",flexShrink:0,
      background:`linear-gradient(135deg,${color},${color}99)`,
      display:"flex",alignItems:"center",justifyContent:"center",
      fontSize:13,fontWeight:700,color:"white"}}>
      {initials}
    </div>
  );
}

// ── Role badge ────────────────────────────────────────────────────────────────
function RoleBadge({role}: {role:string}) {
  const s = ROLE_STYLE[role] || {bg:"#F3F4F6",text:"#6B7280"};
  const label = ROLES.find(r=>r.value===role)?.label || role;
  return (
    <span style={{fontSize:11,fontWeight:600,padding:"3px 10px",
      borderRadius:20,whiteSpace:"nowrap",
      background:s.bg,color:s.text}}>
      {label}
    </span>
  );
}

// ── Status dot ────────────────────────────────────────────────────────────────
function StatusDot({active}: {active:boolean}) {
  return (
    <div style={{display:"flex",alignItems:"center",gap:5}}>
      <div style={{width:6,height:6,borderRadius:"50%",
        background:active?C.success:"#D1D5DB",
        boxShadow:active?`0 0 4px ${C.success}60`:"none"}}/>
      <span style={{fontSize:12,color:active?C.success:C.muted,fontWeight:500}}>
        {active?"Active":"Disabled"}
      </span>
    </div>
  );
}

// ── Kebab menu ────────────────────────────────────────────────────────────────
function KebabMenu({user, onRoleChange, onToggle, onDelete, busy}: {
  user:any; onRoleChange:(id:string,role:string)=>void;
  onToggle:(id:string,active:boolean)=>void;
  onDelete:(id:string)=>void;
  busy:boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(()=>{
    const handler = (e:MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  },[open]);

  return (
    <div ref={ref} style={{position:"relative"}}>
      <button onClick={()=>setOpen(!open)} disabled={busy}
        style={{width:28,height:28,borderRadius:6,border:`1px solid ${C.border}`,
          background:C.surface,cursor:"pointer",
          display:"flex",alignItems:"center",justifyContent:"center",
          color:C.muted,transition:"all 0.15s"}}
        onMouseEnter={e=>{(e.currentTarget as HTMLElement).style.borderColor=C.primary;
          (e.currentTarget as HTMLElement).style.color=C.primary;}}
        onMouseLeave={e=>{(e.currentTarget as HTMLElement).style.borderColor=C.border;
          (e.currentTarget as HTMLElement).style.color=C.muted;}}>
        <MoreVertical size={13}/>
      </button>
      {open && (
        <div style={{position:"absolute",right:0,top:32,width:180,
          background:C.surface,border:`1px solid ${C.border}`,
          borderRadius:10,boxShadow:"0 8px 24px rgba(0,0,0,0.12)",
          zIndex:100,overflow:"hidden",padding:"4px"}}>
          {/* Change role submenu */}
          <div style={{padding:"6px 12px",fontSize:10,fontWeight:700,
            color:C.muted,textTransform:"uppercase",letterSpacing:"0.06em"}}>
            Change Role
          </div>
          {ROLES.map(r=>(
            <button key={r.value} onClick={()=>{onRoleChange(user.id,r.value);setOpen(false);}}
              style={{width:"100%",padding:"7px 12px",border:"none",
                background:user.role===r.value?C.primaryLight:"transparent",
                color:user.role===r.value?C.primary:C.body,
                fontSize:12,fontWeight:user.role===r.value?700:400,
                cursor:"pointer",textAlign:"left",borderRadius:6,
                display:"flex",alignItems:"center",gap:6}}>
              {user.role===r.value&&<Check size={10}/>}
              {r.label}
            </button>
          ))}
          <div style={{height:1,background:C.border,margin:"4px 0"}}/>
          <button onClick={()=>{onToggle(user.id,!user.is_active);setOpen(false);}}
            style={{width:"100%",padding:"7px 12px",border:"none",
              background:"transparent",color:user.is_active?C.warning:C.success,
              fontSize:12,fontWeight:600,cursor:"pointer",textAlign:"left",borderRadius:6}}>
            {user.is_active?"⏸ Disable User":"▶ Enable User"}
          </button>
          <button onClick={()=>{onDelete(user.id);setOpen(false);}}
            style={{width:"100%",padding:"7px 12px",border:"none",
              background:"transparent",color:C.error,
              fontSize:12,fontWeight:600,cursor:"pointer",textAlign:"left",borderRadius:6}}>
            🗑 Delete User
          </button>
        </div>
      )}
    </div>
  );
}

// ── Invite Modal ──────────────────────────────────────────────────────────────
function InviteModal({onClose, onInvite}: {onClose:()=>void; onInvite:(data:any)=>Promise<void>}) {
  const [email, setEmail]   = useState("");
  const [name, setName]     = useState("");
  const [role, setRole]     = useState("business_viewer");
  const [busy, setBusy]     = useState(false);
  const [err, setErr]       = useState("");

  const submit = async (e:React.FormEvent) => {
    e.preventDefault();
    if (!email) { setErr("Email is required"); return; }
    setBusy(true); setErr("");
    try { await onInvite({email,full_name:name,role}); onClose(); }
    catch(e:any) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",
      display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000}}>
      <div style={{background:C.surface,borderRadius:16,padding:28,
        width:"100%",maxWidth:440,boxShadow:"0 20px 60px rgba(0,0,0,0.2)"}}>
        <div style={{display:"flex",justifyContent:"space-between",
          alignItems:"center",marginBottom:20}}>
          <div>
            <h3 style={{fontSize:18,fontWeight:700,color:C.heading,marginBottom:2}}>
              Invite Team Member
            </h3>
            <p style={{fontSize:12,color:C.muted}}>
              They'll receive an email with a sign-in link
            </p>
          </div>
          <button onClick={onClose}
            style={{background:"none",border:"none",cursor:"pointer",
              color:C.muted,padding:4}}>
            <X size={18}/>
          </button>
        </div>
        {err && (
          <div style={{padding:"8px 12px",borderRadius:8,marginBottom:12,
            background:"#FEF2F2",color:C.error,fontSize:13}}>{err}</div>
        )}
        <form onSubmit={submit}>
          <div style={{marginBottom:14}}>
            <label style={{fontSize:12,fontWeight:600,color:C.heading,
              display:"block",marginBottom:6}}>Full Name</label>
            <input value={name} onChange={e=>setName(e.target.value)}
              placeholder="Jane Smith"
              style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,
                borderRadius:8,fontSize:13,outline:"none",boxSizing:"border-box"}}/>
          </div>
          <div style={{marginBottom:14}}>
            <label style={{fontSize:12,fontWeight:600,color:C.heading,
              display:"block",marginBottom:6}}>Email Address *</label>
            <input type="email" value={email} onChange={e=>setEmail(e.target.value)}
              placeholder="jane@company.com" required
              style={{width:"100%",padding:"10px 12px",
                border:`1.5px solid ${!email&&err?C.error:C.border}`,
                borderRadius:8,fontSize:13,outline:"none",boxSizing:"border-box"}}/>
          </div>
          <div style={{marginBottom:20}}>
            <label style={{fontSize:12,fontWeight:600,color:C.heading,
              display:"block",marginBottom:6}}>Role</label>
            <select value={role} onChange={e=>setRole(e.target.value)}
              style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,
                borderRadius:8,fontSize:13,background:C.surface,
                boxSizing:"border-box"}}>
              {ROLES.map(r=>(
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>
          <div style={{display:"flex",gap:10}}>
            <button type="button" onClick={onClose}
              style={{flex:1,padding:"10px",border:`1px solid ${C.border}`,
                borderRadius:8,background:"none",cursor:"pointer",
                fontSize:13,color:C.body}}>Cancel</button>
            <button type="submit" disabled={busy}
              style={{flex:2,padding:"10px",border:"none",borderRadius:8,
                background:C.primary,color:"white",cursor:"pointer",
                fontSize:13,fontWeight:700,
                display:"flex",alignItems:"center",justifyContent:"center",gap:6}}>
              {busy?(
                <><div style={{width:14,height:14,borderRadius:"50%",
                  border:"2px solid rgba(255,255,255,0.3)",borderTopColor:"white",
                  animation:"spin 0.8s linear infinite"}}/>Sending...</>
              ):(
                <><UserPlus size={14}/> Send Invite</>
              )}
            </button>
          </div>
        </form>
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function UsersPage() {
  const { user: currentUser } = useAuthStore();
  const isAdmin = ["super_admin","dept_admin"].includes(currentUser?.role||"");

  const [data, setData]         = useState<any>(null);
  const [loading, setLoading]   = useState(true);
  const [msg, setMsg]           = useState("");
  const [busy, setBusy]         = useState<string|null>(null);
  const [showInvite, setShowInvite] = useState(false);
  const [search, setSearch]     = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const load = () => {
    setLoading(true);
    usersAPI.list().then(setData).finally(()=>setLoading(false));
  };
  useEffect(()=>{ load(); },[]);

  const showMsg = (m:string) => { setMsg(m); setTimeout(()=>setMsg(""),5000); };

  const handleInvite = async (invData:any) => {
    const result = await usersAPI.invite(invData);
    const link = (result as any)?.invite_url || "";
    showMsg(link?`✅ Invited! Link: ${link}`:`✅ Invitation sent to ${invData.email}`);
    load();
  };

  const changeRole = async (userId:string, role:string) => {
    setBusy(`role-${userId}`);
    try {
      const r = await fetch(`${API}/api/v1/users/${userId}/role`,{
        method:"PATCH",
        headers:{Authorization:`Bearer ${getToken()}`,"Content-Type":"application/json"},
        body:JSON.stringify({role}),
      });
      if(!r.ok) throw new Error((await r.json()).detail);
      showMsg("✅ Role updated"); load();
    } catch(e:any) { showMsg(`❌ ${e.message}`); }
    finally { setBusy(null); }
  };

  const toggleActive = async (userId:string, active:boolean) => {
    setBusy(`toggle-${userId}`);
    try {
      const r = await fetch(`${API}/api/v1/users/${userId}/status`,{
        method:"PATCH",
        headers:{Authorization:`Bearer ${getToken()}`,"Content-Type":"application/json"},
        body:JSON.stringify({is_active:active}),
      });
      if(!r.ok) throw new Error((await r.json()).detail);
      showMsg(`✅ User ${active?"enabled":"disabled"}`); load();
    } catch(e:any) { showMsg(`❌ ${e.message}`); }
    finally { setBusy(null); }
  };

  const deleteUser = async (userId:string) => {
    if(!confirm("Delete this user? This cannot be undone.")) return;
    setBusy(`del-${userId}`);
    try {
      const r = await fetch(`${API}/api/v1/users/${userId}`,{
        method:"DELETE",
        headers:{Authorization:`Bearer ${getToken()}`},
      });
      if(!r.ok) throw new Error((await r.json()).detail);
      showMsg("✅ User deleted"); load();
    } catch(e:any) { showMsg(`❌ ${e.message}`); }
    finally { setBusy(null); }
  };

  const bulkDisable = async () => {
    for (const id of selected) await toggleActive(id, false);
    setSelected(new Set());
  };

  const bulkDelete = async () => {
    if(!confirm(`Delete ${selected.size} users?`)) return;
    for (const id of selected) await deleteUser(id);
    setSelected(new Set());
  };

  // Filtered users
  const users: any[] = data?.users || [];
  const plan   = data?.plan || "free";
  const maxSeats = data?.max_users || 50;

  const filtered = useMemo(()=>{
    let list = users;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(u=>
        (u.full_name||"").toLowerCase().includes(q)||
        (u.email||"").toLowerCase().includes(q));
    }
    if (roleFilter) list = list.filter(u=>u.role===roleFilter);
    if (statusFilter==="active") list = list.filter(u=>u.is_active);
    if (statusFilter==="disabled") list = list.filter(u=>!u.is_active);
    return list;
  },[users,search,roleFilter,statusFilter]);

  const seatPct = Math.min((users.length/maxSeats)*100, 100);

  return (
    <div style={{padding:"32px 36px",maxWidth:1100,margin:"0 auto"}}>

      {/* Header */}
      <div style={{display:"flex",justifyContent:"space-between",
        alignItems:"flex-start",marginBottom:24}}>
        <div>
          <h1 style={{fontSize:22,fontWeight:800,color:C.heading,marginBottom:4}}>
            Users & Team
          </h1>
          <div style={{display:"flex",alignItems:"center",gap:12}}>
            <span style={{fontSize:13,color:C.muted}}>
              {users.length}/{maxSeats} seats used · {plan} plan
            </span>
            {/* Seat usage bar */}
            <div style={{width:80,height:6,background:C.border,borderRadius:3,overflow:"hidden"}}>
              <div style={{height:"100%",borderRadius:3,
                width:`${seatPct}%`,
                background:seatPct>90?C.error:seatPct>70?C.warning:C.primary,
                transition:"width 0.5s"}}/>
            </div>
          </div>
        </div>
        {isAdmin && (
          <button onClick={()=>setShowInvite(true)}
            style={{display:"flex",alignItems:"center",gap:8,
              padding:"10px 20px",background:C.primary,color:"white",
              border:"none",borderRadius:10,fontSize:13,fontWeight:700,
              cursor:"pointer",boxShadow:`0 2px 8px ${C.primary}30`}}>
            <UserPlus size={14}/> Invite User
          </button>
        )}
      </div>

      {/* Message */}
      {msg && (
        <div style={{padding:"10px 16px",borderRadius:8,marginBottom:16,
          background:msg.startsWith("✅")?"#F0FDF4":"#FEF2F2",
          color:msg.startsWith("✅")?C.success:C.error,fontSize:13}}>
          {msg}
        </div>
      )}

      {/* Search + filters */}
      <div style={{display:"flex",gap:10,marginBottom:16,flexWrap:"wrap"}}>
        <div style={{position:"relative",flex:1,minWidth:200}}>
          <Search size={13} style={{position:"absolute",left:10,top:"50%",
            transform:"translateY(-50%)",color:C.muted}}/>
          <input value={search} onChange={e=>setSearch(e.target.value)}
            placeholder="Search users..."
            style={{width:"100%",padding:"9px 12px 9px 32px",
              border:`1.5px solid ${C.border}`,borderRadius:8,
              fontSize:13,background:C.surface,boxSizing:"border-box",outline:"none"}}/>
        </div>
        <select value={roleFilter} onChange={e=>setRoleFilter(e.target.value)}
          style={{padding:"9px 12px",border:`1.5px solid ${C.border}`,
            borderRadius:8,fontSize:13,background:C.surface,color:C.body}}>
          <option value="">All Roles</option>
          {ROLES.map(r=><option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
        <select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}
          style={{padding:"9px 12px",border:`1.5px solid ${C.border}`,
            borderRadius:8,fontSize:13,background:C.surface,color:C.body}}>
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="disabled">Disabled</option>
        </select>
        {(search||roleFilter||statusFilter) && (
          <button onClick={()=>{setSearch("");setRoleFilter("");setStatusFilter("");}}
            style={{padding:"9px 12px",background:"#FEF2F2",border:"none",
              borderRadius:8,fontSize:12,color:C.error,cursor:"pointer",fontWeight:600}}>
            ✕ Clear
          </button>
        )}
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div style={{padding:"10px 16px",borderRadius:8,marginBottom:12,
          background:C.primaryLight,border:`1px solid ${C.primary}30`,
          display:"flex",alignItems:"center",gap:12}}>
          <span style={{fontSize:13,fontWeight:600,color:C.primary}}>
            {selected.size} selected
          </span>
          <button onClick={bulkDisable}
            style={{padding:"5px 12px",border:`1px solid ${C.warning}`,
              borderRadius:6,background:"#FFFBEB",color:C.warning,
              fontSize:12,fontWeight:600,cursor:"pointer"}}>
            ⏸ Disable All
          </button>
          <button onClick={bulkDelete}
            style={{padding:"5px 12px",border:`1px solid ${C.error}`,
              borderRadius:6,background:"#FEF2F2",color:C.error,
              fontSize:12,fontWeight:600,cursor:"pointer"}}>
            🗑 Delete All
          </button>
          <button onClick={()=>setSelected(new Set())}
            style={{marginLeft:"auto",background:"none",border:"none",
              cursor:"pointer",color:C.muted,fontSize:12}}>
            Cancel
          </button>
        </div>
      )}

      {/* Table */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,
        borderRadius:12,overflow:"visible",
        position:"relative"}}>
        {/* Table header */}
        <div style={{display:"grid",
          gridTemplateColumns:"36px 1fr 140px 100px 110px 110px 70px",
          padding:"10px 20px",background:C.bg,
          borderRadius:"12px 12px 0 0",
          borderBottom:`1px solid ${C.border}`,
          fontSize:11,fontWeight:700,color:C.muted,
          textTransform:"uppercase",letterSpacing:"0.05em",
          alignItems:"center",gap:12}}>
          <input type="checkbox"
            checked={selected.size===filtered.length&&filtered.length>0}
            onChange={e=>setSelected(e.target.checked
              ? new Set(filtered.map(u=>u.id)) : new Set())}
            style={{accentColor:C.primary}}/>
          <div>User</div>
          <div>Role</div>
          <div>Status</div>
          <div>Joined</div>
          <div>Last Active</div>
          <div>Actions</div>
        </div>

        {loading ? (
          <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading...</div>
        ) : filtered.length===0 ? (
          <div style={{padding:40,textAlign:"center"}}>
            <div style={{fontSize:32,marginBottom:8}}>👥</div>
            <div style={{fontSize:14,fontWeight:600,color:C.heading,marginBottom:4}}>
              No users found
            </div>
            <div style={{fontSize:12,color:C.muted}}>
              {search||roleFilter||statusFilter?"Try different filters":"Invite your first team member"}
            </div>
          </div>
        ) : filtered.map(u=>(
          <div key={u.id}
            style={{display:"grid",
              gridTemplateColumns:"36px 1fr 140px 100px 110px 110px 70px",
              padding:"14px 20px",borderBottom:`1px solid ${C.border}`,
              alignItems:"center",gap:12,
              background:selected.has(u.id)?`${C.primary}05`:C.surface,
              transition:"background 0.1s"}}
            onMouseEnter={e=>!selected.has(u.id)&&((e.currentTarget as HTMLElement).style.background=C.bg)}
            onMouseLeave={e=>!selected.has(u.id)&&((e.currentTarget as HTMLElement).style.background=C.surface)}>

            {/* Checkbox */}
            <input type="checkbox"
              checked={selected.has(u.id)}
              onChange={e=>{
                const s = new Set(selected);
                e.target.checked ? s.add(u.id) : s.delete(u.id);
                setSelected(s);
              }}
              style={{accentColor:C.primary}}/>

            {/* User info */}
            <div style={{display:"flex",alignItems:"center",gap:10,minWidth:0}}>
              <Avatar name={u.full_name} email={u.email}/>
              <div style={{minWidth:0}}>
                <div style={{fontSize:13,fontWeight:700,color:C.heading,
                  overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                  {u.full_name||"—"}
                  {u.id===currentUser?.id&&(
                    <span style={{fontSize:10,marginLeft:6,fontWeight:600,
                      padding:"1px 6px",borderRadius:20,
                      background:C.primaryLight,color:C.primary}}>You</span>
                  )}
                </div>
                <div style={{fontSize:11,color:C.muted,
                  overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                  {u.email}
                </div>
              </div>
            </div>

            {/* Role */}
            <div><RoleBadge role={u.role}/></div>

            {/* Status */}
            <div><StatusDot active={u.is_active}/></div>

            {/* Joined */}
            <div style={{fontSize:12,color:C.muted}}>
              {u.created_at
                ? new Date(u.created_at).toLocaleDateString("en-IN",
                    {day:"2-digit",month:"short",year:"numeric"})
                : "—"}
            </div>

            {/* Last active */}
            <div style={{fontSize:12,color:C.muted}}>
              {relTime(u.last_login_at || u.updated_at)}
            </div>

            {/* Actions */}
            <div style={{display:"flex",gap:6,alignItems:"center"}}>
              {isAdmin && u.id !== currentUser?.id && (
                <KebabMenu user={u}
                  onRoleChange={changeRole}
                  onToggle={toggleActive}
                  onDelete={deleteUser}
                  busy={busy?.startsWith(u.id)||false}/>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Footer count */}
      <div style={{fontSize:12,color:C.muted,marginTop:12,textAlign:"right"}}>
        Showing {filtered.length} of {users.length} users
      </div>

      {/* Invite modal */}
      {showInvite && (
        <InviteModal onClose={()=>setShowInvite(false)} onInvite={handleInvite}/>
      )}

      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
