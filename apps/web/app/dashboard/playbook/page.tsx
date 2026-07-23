"use client";
import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";

const API = "http://localhost:8000";
const C = { primary:"#5B4BFF", primaryLight:"#EEF0FF", heading:"#111827", body:"#374151", muted:"#6B7280", border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC", error:"#EF4444", success:"#22C55E", warning:"#F59E0B" };

const CLAUSE_TYPES = ["liability","payment","termination","confidentiality","indemnification","governing_law","dispute_resolution","ip_ownership","force_majeure","auto_renewal","duration","other"];

export default function PlaybookPage() {
  const [clauses, setClauses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ clause_type:"liability", title:"", standard_text:"", notes:"", risk_guidance:"", is_required:false });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setLoading(true);
    const token = getToken();
    const r = await fetch(`${API}/api/v1/playbook/`, {headers:{Authorization:`Bearer ${token}`}});
    if (r.ok) { const d = await r.json(); setClauses(d.playbook||[]); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.title||!form.standard_text) return;
    setSaving(true); setMsg("");
    const token = getToken();
    try {
      const r = await fetch(`${API}/api/v1/playbook/`, {
        method:"POST", headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},
        body:JSON.stringify(form),
      });
      if (!r.ok) throw new Error((await r.json()).detail);
      setMsg("✅ Clause added to playbook");
      setShowForm(false); setForm({clause_type:"liability",title:"",standard_text:"",notes:"",risk_guidance:"",is_required:false});
      load();
    } catch(e:any) { setMsg(`❌ ${e.message}`); }
    finally { setSaving(false); }
  };

  const deleteClause = async (id:string) => {
    const token = getToken();
    await fetch(`${API}/api/v1/playbook/${id}`, {method:"DELETE",headers:{Authorization:`Bearer ${token}`}});
    load();
  };

  return (
    <div style={{padding:"32px 36px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:28}}>
        <div>
          <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Playbook</h1>
          <p style={{fontSize:14,color:C.muted}}>Standard clause templates your legal team has approved</p>
        </div>
        <button onClick={()=>setShowForm(!showForm)}
          style={{padding:"10px 20px",background:C.primary,color:"white",border:"none",borderRadius:8,fontSize:14,fontWeight:600,cursor:"pointer"}}>
          + Add clause
        </button>
      </div>

      {msg && <div style={{padding:"10px 16px",borderRadius:8,marginBottom:16,background:msg.startsWith("✅")?"#F0FDF4":"#FEF2F2",color:msg.startsWith("✅")?C.success:C.error,fontSize:13}}>{msg}</div>}

      {/* Add form */}
      {showForm && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24,marginBottom:24}}>
          <h2 style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:16}}>Add standard clause</h2>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:16}}>
            <div>
              <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Clause type</label>
              <select value={form.clause_type} onChange={e=>setForm({...form,clause_type:e.target.value})}
                style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}>
                {CLAUSE_TYPES.map(t=><option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
              </select>
            </div>
            <div>
              <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Title</label>
              <input value={form.title} onChange={e=>setForm({...form,title:e.target.value})}
                placeholder="e.g. Standard Liability Cap"
                style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}/>
            </div>
          </div>
          <div style={{marginBottom:12}}>
            <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Standard clause text</label>
            <textarea value={form.standard_text} onChange={e=>setForm({...form,standard_text:e.target.value})}
              placeholder="Paste your approved standard clause text here..." rows={4}
              style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13,resize:"vertical"}}/>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:16}}>
            <div>
              <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Notes</label>
              <input value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}
                placeholder="When to use this clause..."
                style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}/>
            </div>
            <div>
              <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Risk guidance</label>
              <input value={form.risk_guidance} onChange={e=>setForm({...form,risk_guidance:e.target.value})}
                placeholder="What to watch out for..."
                style={{width:"100%",padding:"10px 12px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13}}/>
            </div>
          </div>
          <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:20}}>
            <input type="checkbox" checked={form.is_required} onChange={e=>setForm({...form,is_required:e.target.checked})} id="required"/>
            <label htmlFor="required" style={{fontSize:13,color:C.body}}>Required clause (flag contracts missing this)</label>
          </div>
          <div style={{display:"flex",gap:10}}>
            <button onClick={()=>setShowForm(false)} style={{padding:"10px 20px",border:`1px solid ${C.border}`,borderRadius:8,background:"none",fontSize:14,cursor:"pointer"}}>Cancel</button>
            <button onClick={save} disabled={!form.title||!form.standard_text||saving}
              style={{padding:"10px 20px",border:"none",borderRadius:8,background:C.primary,color:"white",fontSize:14,fontWeight:600,cursor:"pointer"}}>
              {saving?"Saving...":"Save to playbook"}
            </button>
          </div>
        </div>
      )}

      {/* Playbook list */}
      {loading ? <div style={{textAlign:"center",padding:60,color:C.muted}}>Loading...</div>
      : clauses.length===0 ? (
        <div style={{textAlign:"center",padding:80,background:C.surface,border:`1px solid ${C.border}`,borderRadius:12}}>
          <div style={{fontSize:48,marginBottom:16}}>📚</div>
          <p style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:8}}>Playbook is empty</p>
          <p style={{fontSize:14,color:C.muted,marginBottom:20}}>Add your approved standard clauses to compare against contracts</p>
          <button onClick={()=>setShowForm(true)} style={{padding:"10px 24px",background:C.primary,color:"white",border:"none",borderRadius:8,fontSize:14,fontWeight:600,cursor:"pointer"}}>Add first clause</button>
        </div>
      ) : (
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          {clauses.map(cl=>(
            <div key={cl.id} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:20}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:10}}>
                <div>
                  <div style={{display:"flex",gap:8,marginBottom:6}}>
                    <span style={{fontSize:11,fontWeight:700,color:C.primary,background:C.primaryLight,padding:"2px 8px",borderRadius:20,textTransform:"uppercase"}}>{cl.clause_type.replace(/_/g," ")}</span>
                    {cl.is_required && <span style={{fontSize:11,fontWeight:700,color:C.error,background:"#FEF2F2",padding:"2px 8px",borderRadius:20}}>REQUIRED</span>}
                  </div>
                  <h3 style={{fontSize:15,fontWeight:700,color:C.heading}}>{cl.title}</h3>
                </div>
                <button onClick={()=>deleteClause(cl.id)} style={{padding:"4px 12px",border:`1px solid ${C.border}`,borderRadius:6,background:"none",fontSize:12,color:C.muted,cursor:"pointer"}}>Remove</button>
              </div>
              <p style={{fontSize:13,color:C.body,lineHeight:1.6,marginBottom:cl.notes?10:0,fontFamily:"monospace",background:C.bg,padding:"10px 14px",borderRadius:8}}>
                {cl.standard_text.slice(0,200)}{cl.standard_text.length>200?"...":""}
              </p>
              {cl.notes && <p style={{fontSize:12,color:C.muted,marginTop:8}}>📝 {cl.notes}</p>}
              {cl.risk_guidance && <p style={{fontSize:12,color:C.warning,marginTop:4}}>⚠️ {cl.risk_guidance}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
