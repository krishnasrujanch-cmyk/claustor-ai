"use client";
import { API_URL as API } from "@/lib/config";
export const dynamic = "force-dynamic";
import { useEffect, useState, useMemo } from "react";
import { getToken } from "@/lib/api";
import { Pagination } from "@/components/shared/Pagination";
import { C } from "@/lib/design-tokens";


const PAGE_SIZE = 10;
const URGENCY_COLOR: Record<string,string> = {
  urgent:"#EF4444", high:"#F97316", normal:"#F59E0B", low:"#22C55E"
};

function calcUrgency(due_date: string|null, days: number|null): string {
  if (!due_date) return "no_date";
  if (days === null) return "normal";
  if (days < 0)  return "overdue";
  if (days <= 7)  return "urgent";
  if (days <= 30) return "high";
  return "normal";
}

export default function ObligationsPage() {
  const [raw, setRaw]             = useState<any[]>([]);
  const [alerts, setAlerts]       = useState<any>(null);
  const [loading, setLoading]     = useState(true);
  const [completing, setCompleting] = useState<string|null>(null);
  const [page, setPage]           = useState(1);

  // Filters
  const [filterStatus,  setFilterStatus]  = useState("all");
  const [filterType,    setFilterType]    = useState("all");
  const [filterParty,   setFilterParty]   = useState("all");
  const [filterUrgency, setFilterUrgency] = useState("all");
  const [search,        setSearch]        = useState("");

  const load = async () => {
    setLoading(true);
    const token = getToken();
    const h = { Authorization: `Bearer ${token}` };
    try {
      const [obR, alertR] = await Promise.all([
        fetch(`${API}/api/v1/obligations/`, { headers: h }).then(r => r.json()),
        fetch(`${API}/api/v1/alerts/upcoming?days=90&my_contracts_only=true`, { headers: h }).then(r => r.json()),
      ]);
      setRaw(obR.obligations || []);
      setAlerts(alertR);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  // Enrich with calculated fields
  const enriched = useMemo(() => {
    const today = new Date(); today.setHours(0,0,0,0);
    return raw.map(ob => {
      let days_until_due: number|null = null;
      if (ob.due_date) {
        const due = new Date(ob.due_date);
        days_until_due = Math.ceil((due.getTime() - today.getTime()) / 86400000);
      }
      const computedStatus = (ob.status === "pending" && days_until_due !== null && days_until_due < 0)
        ? "overdue" : ob.status;
      return { ...ob, days_until_due, computedStatus };
    });
  }, [raw]);

  // Unique values for dropdowns
  const types    = useMemo(() => [...new Set(enriched.map((o:any) => o.obligation_type).filter(Boolean))], [enriched]);
  const parties  = useMemo(() => [...new Set(enriched.map((o:any) => o.party).filter(Boolean))], [enriched]);

  // Apply filters
  const filtered = useMemo(() => enriched.filter((ob:any) => {
    if (filterStatus  !== "all" && ob.computedStatus    !== filterStatus)  return false;
    if (filterType    !== "all" && ob.obligation_type   !== filterType)    return false;
    if (filterParty   !== "all" && ob.party             !== filterParty)   return false;
    if (filterUrgency !== "all" && calcUrgency(ob.due_date, ob.days_until_due) !== filterUrgency) return false;
    if (search && !ob.title?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  }), [enriched, filterStatus, filterType, filterParty, filterUrgency, search]);

  const paginated = filtered.slice((page-1)*PAGE_SIZE, page*PAGE_SIZE);

  const hasFilters = filterStatus!=="all"||filterType!=="all"||filterParty!=="all"||filterUrgency!=="all"||search!=="";

  const markComplete = async (id: string) => {
    setCompleting(id);
    try {
      const r = await fetch(`${API}/api/v1/alerts/obligations/${id}/complete`, {
        method:"POST", headers:{ Authorization:`Bearer ${getToken()}` },
      });
      if (r.ok) setRaw(prev => prev.map(ob => ob.id===id ? {...ob, status:"completed"} : ob));
    } finally { setCompleting(null); }
  };

  return (
    <div style={{padding:"32px 36px"}}>
      <div style={{marginBottom:24}}>
        <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Obligations</h1>
        <p style={{fontSize:14,color:C.muted}}>Track payment dates, renewal notices, and deadlines</p>
      </div>

      {/* Summary cards */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))",gap:16,marginBottom:24}}>
        {[
          {label:"Total",     value:enriched.length,                                          color:C.primary},
          {label:"Pending",   value:enriched.filter((o:any)=>o.computedStatus==="pending").length,   color:C.warning},
          {label:"Overdue",   value:enriched.filter((o:any)=>o.computedStatus==="overdue").length,   color:C.error},
          {label:"Completed", value:enriched.filter((o:any)=>o.computedStatus==="completed").length, color:C.success},
          {label:"Upcoming",  value:alerts?.summary?.total_obligations||0,                     color:C.primary},
        ].map(s=>(
          <div key={s.label} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:10,padding:"16px 20px"}}>
            <div style={{fontSize:12,color:C.muted,marginBottom:4}}>{s.label}</div>
            <div style={{fontSize:24,fontWeight:800,color:s.color}}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:10,
        padding:"12px 16px",marginBottom:16,display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
        <input value={search} onChange={e=>{setSearch(e.target.value);setPage(1);}}
          placeholder="Search obligations..."
          style={{flex:1,minWidth:160,padding:"7px 12px",border:`1px solid ${C.border}`,borderRadius:8,fontSize:13,color:C.body}}/>

        <select value={filterStatus} onChange={e=>{setFilterStatus(e.target.value);setPage(1);}}
          style={{padding:"7px 10px",border:`1px solid ${C.border}`,borderRadius:8,fontSize:13,color:C.body}}>
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="completed">Completed</option>
          <option value="overdue">Overdue</option>
        </select>

        <select value={filterType} onChange={e=>{setFilterType(e.target.value);setPage(1);}}
          style={{padding:"7px 10px",border:`1px solid ${C.border}`,borderRadius:8,fontSize:13,color:C.body}}>
          <option value="all">All Types</option>
          {types.map((t:any)=><option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
        </select>

        <select value={filterParty} onChange={e=>{setFilterParty(e.target.value);setPage(1);}}
          style={{padding:"7px 10px",border:`1px solid ${C.border}`,borderRadius:8,fontSize:13,color:C.body}}>
          <option value="all">All Parties</option>
          {parties.map((p:any)=><option key={p} value={p}>{p}</option>)}
        </select>

        <select value={filterUrgency} onChange={e=>{setFilterUrgency(e.target.value);setPage(1);}}
          style={{padding:"7px 10px",border:`1px solid ${C.border}`,borderRadius:8,fontSize:13,color:C.body}}>
          <option value="all">All Urgency</option>
          <option value="overdue">Overdue</option>
          <option value="urgent">Urgent (≤7d)</option>
          <option value="high">High (≤30d)</option>
          <option value="normal">Normal</option>
          <option value="no_date">No date</option>
        </select>

        {hasFilters && (
          <button onClick={()=>{setFilterStatus("all");setFilterType("all");setFilterParty("all");setFilterUrgency("all");setSearch("");setPage(1);}}
            style={{padding:"7px 10px",background:"#F3F4F6",border:"none",borderRadius:8,fontSize:12,color:C.muted,cursor:"pointer"}}>
            Clear ×
          </button>
        )}
        <span style={{fontSize:13,color:C.muted,marginLeft:"auto"}}>{filtered.length} of {enriched.length}</span>
      </div>

      {/* Table */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden"}}>
        {loading ? (
          <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading...</div>
        ) : filtered.length===0 ? (
          <div style={{padding:40,textAlign:"center",color:C.muted}}>
            {hasFilters?"No obligations match filters":"No obligations found"}
          </div>
        ) : (
          <>
            <table style={{width:"100%",borderCollapse:"collapse"}}>
              <thead>
                <tr style={{background:C.bg,borderBottom:`1px solid ${C.border}`}}>
                  {["Title","Type","Party","Due Date","Amount","Urgency","Status","Action"].map(h=>(
                    <th key={h} style={{padding:"10px 16px",textAlign:"left",fontSize:11,fontWeight:700,color:C.muted,textTransform:"uppercase"}}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {paginated.map((ob:any)=>(
                  <tr key={ob.id} style={{borderBottom:`1px solid ${C.border}`,opacity:ob.status==="completed"?0.6:1}}>
                    <td style={{padding:"12px 16px"}}>
                      <div style={{fontSize:13,fontWeight:600,color:C.heading}}>{ob.title}</div>
                      {ob.description && <div style={{fontSize:11,color:C.muted}}>{ob.description.slice(0,60)}...</div>}
                    </td>
                    <td style={{padding:"12px 16px"}}>
                      <span style={{fontSize:12,padding:"2px 8px",borderRadius:20,background:C.primaryLight,color:C.primary,fontWeight:600}}>
                        {(ob.obligation_type||"other").replace(/_/g," ")}
                      </span>
                    </td>
                    <td style={{padding:"12px 16px",fontSize:13,color:C.body,textTransform:"capitalize"}}>{ob.party||"—"}</td>
                    <td style={{padding:"12px 16px"}}>
                      {ob.due_date ? (
                        <>
                          <div style={{fontSize:13,fontWeight:600,color:ob.days_until_due<0?C.error:ob.days_until_due<=30?C.warning:C.body}}>
                            {new Date(ob.due_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}
                          </div>
                          {ob.status!=="completed" && (
                            <div style={{fontSize:11,color:C.muted}}>
                              {ob.days_until_due<0?`${Math.abs(ob.days_until_due)}d overdue`:`in ${ob.days_until_due}d`}
                            </div>
                          )}
                        </>
                      ) : <span style={{color:C.muted,fontSize:13}}>—</span>}
                    </td>
                    <td style={{padding:"12px 16px",fontSize:13,color:C.body}}>
                      {ob.amount?`${ob.currency||"USD"} ${Number(ob.amount).toLocaleString()}`:"—"}
                    </td>
                    <td style={{padding:"12px 16px"}}>
                      {(() => {
                        const u = calcUrgency(ob.due_date, ob.days_until_due);
                        return (
                          <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:20,
                            background:`${URGENCY_COLOR[u]||C.muted}18`,color:URGENCY_COLOR[u]||C.muted}}>
                            {u==="no_date"?"—":u}
                          </span>
                        );
                      })()}
                    </td>
                    <td style={{padding:"12px 16px"}}>
                      <span style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,
                        background:ob.computedStatus==="completed"?"#F0FDF4":ob.computedStatus==="overdue"?"#FEF2F2":"#FFFBEB",
                        color:ob.computedStatus==="completed"?C.success:ob.computedStatus==="overdue"?C.error:C.warning}}>
                        {ob.computedStatus||"pending"}
                      </span>
                    </td>
                    <td style={{padding:"12px 16px"}}>
                      {ob.status!=="completed" && (
                        <button onClick={()=>markComplete(ob.id)} disabled={completing===ob.id}
                          style={{padding:"5px 12px",fontSize:12,fontWeight:600,background:C.success,
                            color:"white",border:"none",borderRadius:6,cursor:"pointer"}}>
                          {completing===ob.id?"...":"✓ Done"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination
              page={page}
              totalPages={Math.ceil(filtered.length/PAGE_SIZE)}
              total={filtered.length}
              pageSize={PAGE_SIZE}
              onPage={setPage}
            />
          </>
        )}
      </div>
    </div>
  );
}
