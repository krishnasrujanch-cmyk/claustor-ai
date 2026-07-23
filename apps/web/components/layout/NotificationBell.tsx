"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getToken } from "@/lib/api";

const API = "http://localhost:8000";
const C = {
  primary:"#5B4BFF", heading:"#111827", body:"#374151",
  muted:"#6B7280", border:"#E5E7EB", surface:"#FFFFFF",
  error:"#EF4444", warning:"#F59E0B",
};

export function NotificationBell() {
  const [open, setOpen]         = useState(false);
  const [alerts, setAlerts]     = useState<any>(null);
  const [loading, setLoading]   = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const token = getToken();
      try {
        const r = await fetch(`${API}/api/v1/alerts/upcoming?days=30`, {
          headers:{Authorization:`Bearer ${token}`}
        });
        if (r.ok) setAlerts(await r.json());
      } catch(e) {}
      finally { setLoading(false); }
    };
    load();
    // Refresh every 5 minutes
    const interval = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Close on outside click
  useEffect(() => {
    const handler = (e:MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const urgentCount = alerts?.summary?.urgent || 0;
  const totalCount  = (alerts?.summary?.total_renewals || 0) + (alerts?.summary?.total_obligations || 0);

  return (
    <div ref={ref} style={{position:"relative"}}>
      {/* Bell button */}
      <button onClick={()=>setOpen(!open)} style={{
        position:"relative", background:"rgba(255,255,255,0.08)",
        border:"none", borderRadius:8, padding:"6px 10px",
        cursor:"pointer", display:"flex", alignItems:"center",
      }}>
        <span style={{fontSize:18}}>🔔</span>
        {totalCount > 0 && (
          <span style={{
            position:"absolute", top:-4, right:-4,
            width:18, height:18, borderRadius:"50%",
            background:urgentCount>0?C.error:C.warning,
            color:"white", fontSize:10, fontWeight:700,
            display:"flex", alignItems:"center", justifyContent:"center",
          }}>
            {totalCount > 9 ? "9+" : totalCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div style={{
          position:"absolute", top:"100%", right:0, marginTop:8,
          width:320, background:C.surface, border:`1px solid ${C.border}`,
          borderRadius:12, boxShadow:"0 8px 24px rgba(0,0,0,0.12)",
          zIndex:200, overflow:"hidden",
        }}>
          <div style={{padding:"12px 16px",borderBottom:`1px solid ${C.border}`,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span style={{fontSize:14,fontWeight:700,color:C.heading}}>Notifications</span>
            {urgentCount > 0 && (
              <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:20,background:"#FEF2F2",color:C.error}}>
                {urgentCount} urgent
              </span>
            )}
          </div>

          {loading ? (
            <div style={{padding:20,textAlign:"center",color:C.muted,fontSize:13}}>Loading...</div>
          ) : totalCount === 0 ? (
            <div style={{padding:24,textAlign:"center",color:C.muted,fontSize:13}}>
              <div style={{fontSize:32,marginBottom:8}}>✅</div>
              No upcoming alerts
            </div>
          ) : (
            <div style={{maxHeight:320,overflowY:"auto"}}>
              {/* Renewals */}
              {alerts?.renewals?.map((r:any)=>(
                <Link key={r.id} href={`/dashboard/contracts/${r.id}`} onClick={()=>setOpen(false)}
                  style={{display:"block",padding:"12px 16px",borderBottom:`1px solid ${C.border}`,textDecoration:"none",
                    background:r.urgency==="urgent"?"#FEF2F250":C.surface}}>
                  <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
                    <span style={{fontSize:12,fontWeight:700,color:r.urgency==="urgent"?C.error:C.warning}}>
                      {r.urgency==="urgent"?"🚨":"⏰"} Renewal in {r.days_until_expiry}d
                    </span>
                  </div>
                  <div style={{fontSize:13,fontWeight:600,color:C.heading}}>{r.title}</div>
                  <div style={{fontSize:11,color:C.muted,marginTop:2}}>{r.counterparty||""}</div>
                </Link>
              ))}
              {/* Obligations */}
              {alerts?.obligations?.filter((o:any)=>o.due_date)?.slice(0,5).map((o:any)=>(
                <Link key={o.id} href="/dashboard/obligations" onClick={()=>setOpen(false)}
                  style={{display:"block",padding:"12px 16px",borderBottom:`1px solid ${C.border}`,textDecoration:"none",
                    background:o.urgency==="urgent"?"#FFFBEB50":C.surface}}>
                  <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
                    <span style={{fontSize:12,fontWeight:700,color:o.urgency==="urgent"?C.error:C.warning}}>
                      {o.urgency==="urgent"?"🚨":"📅"} Due in {o.days_until_due}d
                    </span>
                    {o.amount && <span style={{fontSize:11,color:C.muted}}>{o.currency} {o.amount.toLocaleString()}</span>}
                  </div>
                  <div style={{fontSize:13,fontWeight:600,color:C.heading}}>{o.title}</div>
                  <div style={{fontSize:11,color:C.muted,marginTop:2}}>{o.type}</div>
                </Link>
              ))}
            </div>
          )}

          <div style={{padding:"10px 16px",borderTop:`1px solid ${C.border}`}}>
            <Link href="/dashboard/obligations" onClick={()=>setOpen(false)}
              style={{fontSize:13,color:C.primary,textDecoration:"none",fontWeight:600}}>
              View all obligations →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
