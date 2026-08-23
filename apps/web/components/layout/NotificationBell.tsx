"use client";
import { API_URL as API } from "@/lib/config";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";



// ── Relative time formatter ────────────────────────────────────────────────────
function relativeTime(dateStr: string): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins  = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days  = Math.floor(diff / 86400000);
  if (mins < 1)   return "just now";
  if (mins < 60)  return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7)   return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-IN", {day:"2-digit", month:"short"});
}

// ── Severity → style map ──────────────────────────────────────────────────────
const SEV: Record<string, {border:string; dot:string; label:string}> = {
  high:   {border:"#EF4444", dot:"#EF4444",  label:"🔴"},
  error:  {border:"#EF4444", dot:"#EF4444",  label:"🔴"},
  medium: {border:"#F59E0B", dot:"#F59E0B",  label:"🟡"},
  low:    {border:"#3B82F6", dot:"#3B82F6",  label:"🔵"},
  info:   {border:"#3B82F6", dot:"#3B82F6",  label:"🔵"},
  review: {border:"#8B5CF6", dot:"#8B5CF6",  label:"📋"},
  task:   {border:"#06B6D4", dot:"#06B6D4",  label:"📅"},
};

function getSev(n: any): string {
  if (n.type === "review_assigned") return "review";
  if (n.type === "obligation")      return "task";
  return n.severity || "info";
}

// ── Notification Item ─────────────────────────────────────────────────────────
function NotifItem({ item, onRead, onNavigate }: {
  item: any; onRead: (id:string)=>void; onNavigate: (href:string)=>void;
}) {
  const [hovered, setHovered] = useState(false);
  const sev = getSev(item);
  const style = SEV[sev] || SEV.info;
  const isUnread = !item.read;
  const href = item.contract_id
    ? `/dashboard/contracts/${item.contract_id}`
    : item.type==="review_assigned" ? "/dashboard/reviews"
    : "/dashboard/obligations";

  return (
    <div
      onMouseEnter={()=>setHovered(true)}
      onMouseLeave={()=>setHovered(false)}
      style={{
        padding:"12px 16px",
        borderBottom:"1px solid #F3F4F6",
        borderLeft:`3px solid ${style.border}`,
        background:hovered?"#F8FAFF":"white",
        transition:"background 0.1s",
        cursor:"pointer",
        position:"relative",
      }}>
      <div style={{display:"flex",alignItems:"flex-start",gap:10}}>
        {/* Unread dot */}
        <div style={{width:7,height:7,borderRadius:"50%",
          background:isUnread?style.dot:"transparent",
          flexShrink:0,marginTop:5,
          boxShadow:isUnread?`0 0 4px ${style.dot}60`:"none"}}/>

        {/* Content */}
        <div style={{flex:1,minWidth:0}}>
          <div style={{fontSize:13,fontWeight:isUnread?700:600,
            color:"#111827",marginBottom:2,
            overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
            {item.title || item.contract_title || "Notification"}
          </div>
          <div style={{fontSize:12,color:"#6B7280",lineHeight:1.4,marginBottom:4}}>
            {item.message || item.description || ""}
          </div>
          <div style={{fontSize:10,color:"#9CA3AF"}}>
            {relativeTime(item.time || item.created_at || item.due_date || "")}
          </div>
        </div>

        {/* Hover actions */}
        <div style={{
          display:"flex",gap:4,flexShrink:0,
          opacity:hovered?1:0,transition:"opacity 0.15s",
        }}>
          {isUnread && (
            <button
              onClick={e=>{e.stopPropagation(); onRead(item.id);}}
              title="Mark as read"
              style={{width:24,height:24,borderRadius:6,border:"1px solid #E5E7EB",
                background:"white",cursor:"pointer",fontSize:11,
                display:"flex",alignItems:"center",justifyContent:"center",
                color:"#22C55E",fontWeight:700}}>
              ✓
            </button>
          )}
          <button
            onClick={e=>{e.stopPropagation(); onNavigate(href);}}
            title="Open"
            style={{width:24,height:24,borderRadius:6,border:"1px solid #E5E7EB",
              background:"white",cursor:"pointer",fontSize:11,
              display:"flex",alignItems:"center",justifyContent:"center",
              color:"#0066FF",fontWeight:700}}>
            →
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Bell ─────────────────────────────────────────────────────────────────
export function NotificationBell() {
  const router = useRouter();
  const [open, setOpen]             = useState(false);
  const [notifications, setNotifs]  = useState<any[]>([]);
  const [alerts, setAlerts]         = useState<any>(null);
  const [loading, setLoading]       = useState(false);
  const [tab, setTab]               = useState<"all"|"unread"|"urgent">("all");
  const [readIds, setReadIds]       = useState<Set<string>>(new Set());
  const ref = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const token = getToken();
    if (!token) { setLoading(false); return; }
    try {
      const [notifR, alertR] = await Promise.all([
        fetch(`${API}/api/v1/notifications/`,
          {headers:{Authorization:`Bearer ${token}`}}).then(r=>r.json()),
        fetch(`${API}/api/v1/alerts/upcoming?days=30&my_contracts_only=true`,
          {headers:{Authorization:`Bearer ${token}`}}).then(r=>r.json()),
      ]);
      setNotifs(notifR.notifications || []);
      setAlerts(alertR);
    } catch(e) {}
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Build unified notification list
  const allItems = [
    ...notifications.map(n=>({...n, _type:"notification"})),
    ...(alerts?.renewals||[]).map((r:any)=>({
      id:`renewal-${r.id}`, _type:"renewal",
      title:r.title, contract_id:r.id,
      message:`Auto-renewal in ${r.days_until_expiry} days`,
      severity:r.urgency==="urgent"?"high":"medium",
      time:r.expiry_date,
    })),
    ...(alerts?.obligations||[]).slice(0,4).map((o:any)=>({
      id:`obl-${o.id}`, _type:"obligation", type:"obligation",
      title:o.title,
      message:`Due in ${o.days_until_due} days${o.amount?` · ${o.currency} ${o.amount?.toLocaleString()}`:""}`,
      severity:"task", time:o.due_date,
    })),
  ];

  const unreadItems  = allItems.filter(n=>!readIds.has(n.id));
  const urgentItems  = allItems.filter(n=>n.severity==="high"||n.severity==="error");
  const unreadCount  = unreadItems.length;
  const urgentCount  = urgentItems.length;
  const totalCount   = allItems.length;

  const displayItems = tab==="unread" ? unreadItems
                     : tab==="urgent" ? urgentItems
                     : allItems;

  // Group by type
  const groups = {
    contracts: displayItems.filter(n=>n._type==="notification"),
    renewals:  displayItems.filter(n=>n._type==="renewal"),
    obligations:displayItems.filter(n=>n._type==="obligation"),
  };

  const markRead = (id: string) => {
    setReadIds(prev=>new Set([...prev, id]));
  };

  const markAllRead = () => {
    setReadIds(new Set(allItems.map(n=>n.id)));
  };

  const handleNavigate = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  return (
    <div ref={ref} style={{position:"relative",flexShrink:0}}>
      {/* Bell button */}
      <button
        onClick={()=>{ setOpen(o=>!o); if(!open) load(); }}
        style={{position:"relative",background:"rgba(255,255,255,0.08)",
          border:"none",borderRadius:8,width:36,height:36,
          display:"flex",alignItems:"center",justifyContent:"center",
          cursor:"pointer",flexShrink:0,transition:"background 0.15s"}}
        onMouseEnter={e=>(e.currentTarget as HTMLElement).style.background="rgba(255,255,255,0.12)"}
        onMouseLeave={e=>(e.currentTarget as HTMLElement).style.background="rgba(255,255,255,0.08)"}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round"
          style={{color:"#94A3B8"}}>
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        {totalCount > 0 && (
          <span style={{position:"absolute",top:-4,right:-4,minWidth:18,height:18,
            borderRadius:9,background:urgentCount>0?"#EF4444":"#0066FF",
            color:"white",fontSize:10,fontWeight:700,
            display:"flex",alignItems:"center",justifyContent:"center",
            padding:"0 4px",boxShadow:"0 2px 4px rgba(0,0,0,0.3)"}}>
            {totalCount>9?"9+":totalCount}
          </span>
        )}
      </button>

      {/* Popover — anchored top-right below bell */}
      {open && (
        <div style={{
          position:"fixed",top:60,right:16,width:380,
          background:"white",border:"1px solid #E5E7EB",
          borderRadius:12,boxShadow:"0 12px 40px rgba(0,0,0,0.16)",
          zIndex:9999,overflow:"hidden",
        }}>
          {/* Caret arrow */}
          <div style={{position:"absolute",top:-6,right:10,
            width:12,height:12,background:"white",
            border:"1px solid #E5E7EB",borderBottom:"none",borderRight:"none",
            transform:"rotate(45deg)",zIndex:10}}/>

          {/* Header */}
          <div style={{padding:"12px 16px",borderBottom:"1px solid #F3F4F6",
            background:"#FAFBFC",display:"flex",
            justifyContent:"space-between",alignItems:"center"}}>
            <div style={{display:"flex",alignItems:"center",gap:8}}>
              <span style={{fontSize:14,fontWeight:700,color:"#111827"}}>
                Notifications
              </span>
              {urgentCount>0 && (
                <span style={{fontSize:10,fontWeight:700,padding:"2px 8px",
                  borderRadius:20,background:"#FEF2F2",color:"#DC2626"}}>
                  {urgentCount} urgent
                </span>
              )}
            </div>
            <div style={{display:"flex",gap:8,alignItems:"center"}}>
              {unreadCount>0 && (
                <button onClick={markAllRead}
                  style={{fontSize:11,color:"#0066FF",fontWeight:600,
                    background:"none",border:"none",cursor:"pointer",padding:0}}>
                  Mark all read
                </button>
              )}
              <button onClick={()=>setOpen(false)}
                style={{background:"none",border:"none",cursor:"pointer",
                  color:"#9CA3AF",fontSize:18,lineHeight:1,padding:0}}>
                ×
              </button>
            </div>
          </div>

          {/* Tab filters */}
          <div style={{padding:"8px 16px",borderBottom:"1px solid #F3F4F6",
            display:"flex",gap:6,background:"white"}}>
            {[
              {key:"all",    label:`All (${totalCount})`},
              {key:"unread", label:`Unread (${unreadCount})`},
              {key:"urgent", label:`Urgent (${urgentCount})`},
            ].map(t=>(
              <button key={t.key} onClick={()=>setTab(t.key as any)}
                style={{padding:"4px 10px",borderRadius:20,border:"none",
                  fontSize:11,fontWeight:600,cursor:"pointer",
                  background:tab===t.key?"#0066FF":"#F3F4F6",
                  color:tab===t.key?"white":"#6B7280",
                  transition:"all 0.15s"}}>
                {t.label}
              </button>
            ))}
          </div>

          {/* Content */}
          {loading ? (
            <div style={{padding:24,textAlign:"center",color:"#6B7280",fontSize:13}}>
              Loading...
            </div>
          ) : displayItems.length===0 ? (
            <div style={{padding:32,textAlign:"center"}}>
              <div style={{fontSize:32,marginBottom:8}}>
                {tab==="urgent"?"🎉":tab==="unread"?"✅":"🔔"}
              </div>
              <p style={{fontSize:13,color:"#6B7280",margin:0}}>
                {tab==="urgent"?"No urgent notifications"
                :tab==="unread"?"All caught up!"
                :"No notifications"}
              </p>
            </div>
          ) : (
            <div style={{maxHeight:420,overflowY:"auto"}}>
              {/* Contracts group */}
              {groups.contracts.length>0 && (
                <>
                  <div style={{padding:"6px 16px",fontSize:10,fontWeight:700,
                    color:"#94A3B8",textTransform:"uppercase",letterSpacing:"0.06em",
                    background:"#FAFBFC",borderBottom:"1px solid #F3F4F6"}}>
                    Contracts
                  </div>
                  {groups.contracts.map(n=>(
                    <NotifItem key={n.id} item={n}
                      onRead={markRead} onNavigate={handleNavigate}/>
                  ))}
                </>
              )}
              {/* Renewals group */}
              {groups.renewals.length>0 && (
                <>
                  <div style={{padding:"6px 16px",fontSize:10,fontWeight:700,
                    color:"#94A3B8",textTransform:"uppercase",letterSpacing:"0.06em",
                    background:"#FAFBFC",borderBottom:"1px solid #F3F4F6"}}>
                    Renewals
                  </div>
                  {groups.renewals.map(n=>(
                    <NotifItem key={n.id} item={n}
                      onRead={markRead} onNavigate={handleNavigate}/>
                  ))}
                </>
              )}
              {/* Obligations group */}
              {groups.obligations.length>0 && (
                <>
                  <div style={{padding:"6px 16px",fontSize:10,fontWeight:700,
                    color:"#94A3B8",textTransform:"uppercase",letterSpacing:"0.06em",
                    background:"#FAFBFC",borderBottom:"1px solid #F3F4F6"}}>
                    Obligations
                  </div>
                  {groups.obligations.map(n=>(
                    <NotifItem key={n.id} item={n}
                      onRead={markRead} onNavigate={handleNavigate}/>
                  ))}
                </>
              )}
            </div>
          )}

          {/* Footer */}
          <div style={{padding:"10px 16px",borderTop:"1px solid #F3F4F6",
            background:"#FAFBFC",display:"flex",
            justifyContent:"space-between",alignItems:"center"}}>
            <button onClick={()=>handleNavigate("/dashboard/obligations")}
              style={{fontSize:13,color:"#0066FF",fontWeight:600,
                background:"none",border:"none",cursor:"pointer",padding:0}}>
              View all notifications →
            </button>
            <span style={{fontSize:11,color:"#9CA3AF"}}>
              {totalCount} total
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
