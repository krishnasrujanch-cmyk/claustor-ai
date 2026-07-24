"use client";
import { useEffect, useState } from "react";
import { billing as billingAPI } from "@/lib/api";

const C = { primary:"#5B4BFF",heading:"#111827",body:"#374151",muted:"#6B7280",border:"#E5E7EB",surface:"#FFFFFF",bg:"#FAFBFC" };

export default function BillingPage() {
  const [summary, setSummary] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([billingAPI.summary(), billingAPI.plans(), billingAPI.invoices()])
      .then(([s, p, inv]) => { setSummary(s); setPlans((p as any).plans); setInvoices((inv as any).invoices); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{padding:40,textAlign:"center",color:C.muted}}>Loading billing...</div>;

  return (
    <div style={{padding:"32px 36px",maxWidth:900}}>
      <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Billing</h1>
      <p style={{fontSize:14,color:C.muted,marginBottom:32}}>Manage your plan and usage</p>
      {summary && (
        <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24,marginBottom:24}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:16}}>
            <div>
              <div style={{fontSize:13,color:C.muted,marginBottom:4}}>Current plan</div>
              <div style={{fontSize:24,fontWeight:800,color:C.primary,textTransform:"capitalize"}}>{summary.plan}</div>
            </div>
            <div style={{textAlign:"right"}}>
              <div style={{fontSize:13,color:C.muted}}>Provider</div>
              <div style={{fontSize:14,fontWeight:600,color:C.body}}>{summary.billing_provider}</div>
            </div>
          </div>
          {summary.usage && Object.entries(summary.usage).map(([k,v]:any)=>(
            <div key={k} style={{marginBottom:12}}>
              <div style={{display:"flex",justifyContent:"space-between",fontSize:13,marginBottom:4}}>
                <span style={{color:C.body,textTransform:"capitalize"}}>{k.replace("_"," ")}</span>
                <span style={{color:C.muted}}>{v.used}/{v.limit}</span>
              </div>
              {v.pct !== undefined && (
                <div style={{height:6,background:C.border,borderRadius:3,overflow:"hidden"}}>
                  <div style={{height:"100%",width:`${Math.min(v.pct,100)}%`,background:v.pct>90?"#EF4444":C.primary,borderRadius:3}}/>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24,marginBottom:24}}>
        <h2 style={{fontSize:16,fontWeight:700,color:C.heading,marginBottom:16}}>Invoice history</h2>
        {invoices.length===0 ? <p style={{color:C.muted,fontSize:14}}>No invoices yet</p> : (
          <table style={{width:"100%",borderCollapse:"collapse"}}>
            <thead><tr>{["Period","Amount","Status"].map(h=><th key={h} style={{padding:"8px 0",textAlign:"left",fontSize:12,fontWeight:600,color:C.muted,borderBottom:`1px solid ${C.border}`}}>{h}</th>)}</tr></thead>
            <tbody>{invoices.map((inv:any)=>(
              <tr key={inv.id} style={{borderBottom:`1px solid ${C.border}`}}>
                <td style={{padding:"12px 0",fontSize:14,color:C.body}}>{new Date(inv.period_start).toLocaleDateString("en-IN",{month:"short",year:"numeric"})}</td>
                <td style={{padding:"12px 0",fontSize:14,fontWeight:600,color:C.heading}}>₹{inv.amount.toLocaleString("en-IN",{maximumFractionDigits:2})}</td>
                <td style={{padding:"12px 0"}}><span style={{fontSize:11,fontWeight:600,padding:"2px 8px",borderRadius:20,background:"#F0FDF4",color:"#16A34A"}}>{inv.status}</span></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
