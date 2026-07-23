"use client";

import { useEffect, useState } from "react";
import { contracts as contractsAPI, Contract, Clause } from "@/lib/api";

const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
  error:"#EF4444", warning:"#F59E0B", success:"#22C55E",
};

function RiskBadge({ level }: { level:string }) {
  const m: Record<string,any> = {
    high:{bg:"#FEF2F2",text:"#DC2626"},
    medium:{bg:"#FFFBEB",text:"#D97706"},
    low:{bg:"#F0FDF4",text:"#16A34A"},
  };
  const c = m[level]||{bg:"#F3F4F6",text:"#6B7280"};
  return <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:20,background:c.bg,color:c.text,textTransform:"uppercase"}}>{level||"—"}</span>;
}

export default function ComparePage() {
  const [allContracts, setAllContracts] = useState<Contract[]>([]);
  const [idA, setIdA] = useState("");
  const [idB, setIdB] = useState("");
  const [contractA, setContractA] = useState<any>(null);
  const [contractB, setContractB] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    contractsAPI.list({status:"analyzed",page_size:50})
      .then(d=>setAllContracts(d.contracts));
  }, []);

  const compare = async () => {
    if (!idA||!idB||idA===idB) return;
    setLoading(true);
    try {
      const [a,b] = await Promise.all([contractsAPI.get(idA), contractsAPI.get(idB)]);
      setContractA(a); setContractB(b);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  // Get all unique clause types across both contracts
  const allClauseTypes = contractA && contractB
    ? [...new Set([
        ...(contractA.clauses||[]).map((c:Clause)=>c.clause_type),
        ...(contractB.clauses||[]).map((c:Clause)=>c.clause_type),
      ])].sort()
    : [];

  const getClause = (contract:any, type:string) =>
    contract?.clauses?.find((c:Clause)=>c.clause_type===type);

  const fieldsToCompare = [
    {label:"Contract Type",    keyA:"contract_type",   keyB:"contract_type"},
    {label:"Counterparty",     keyA:"counterparty",    keyB:"counterparty"},
    {label:"Governing Law",    keyA:"governing_law",   keyB:"governing_law"},
    {label:"Contract Value",   keyA:"contract_value",  keyB:"contract_value", fmt:(v:any,c:any)=>v?`${c.contract_currency||"USD"} ${(v/1000000).toFixed(2)}M`:"—"},
    {label:"Effective Date",   keyA:"effective_date",  keyB:"effective_date", fmt:(v:any)=>v?new Date(v).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):"—"},
    {label:"Expiry Date",      keyA:"expiry_date",     keyB:"expiry_date",    fmt:(v:any)=>v?new Date(v).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):"—"},
    {label:"Auto Renewal",     keyA:"auto_renewal",    keyB:"auto_renewal",   fmt:(v:any)=>v===null?"Unknown":v?"Yes":"No"},
    {label:"Risk Score",       keyA:"risk_score",      keyB:"risk_score",     fmt:(v:any)=>v!==null?Math.round(v):"—"},
    {label:"Risk Level",       keyA:"risk_level",      keyB:"risk_level"},
    {label:"Clause Count",     keyA:"clause_count",    keyB:"clause_count"},
    {label:"Has Signatures",   keyA:"has_signatures",  keyB:"has_signatures", fmt:(v:any)=>v?"Yes":"No"},
  ];

  const isDifferent = (a:any,b:any) => String(a) !== String(b);

  return (
    <div style={{padding:"32px 36px"}}>
      <div style={{marginBottom:28}}>
        <h1 style={{fontSize:24,fontWeight:800,color:C.heading,marginBottom:4}}>Contract Comparison</h1>
        <p style={{fontSize:14,color:C.muted}}>Compare two contracts side by side — clauses, risk, dates, terms</p>
      </div>

      {/* Contract selector */}
      <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,padding:24,marginBottom:24}}>
        <div style={{display:"grid",gridTemplateColumns:"1fr auto 1fr",gap:16,alignItems:"end"}}>
          <div>
            <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Contract A</label>
            <select value={idA} onChange={e=>setIdA(e.target.value)}
              style={{width:"100%",padding:"10px 14px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13,color:C.body}}>
              <option value="">Select contract...</option>
              {allContracts.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>
          <div style={{fontSize:24,color:C.muted,paddingBottom:8,textAlign:"center"}}>⇄</div>
          <div>
            <label style={{display:"block",fontSize:13,fontWeight:600,color:C.body,marginBottom:6}}>Contract B</label>
            <select value={idB} onChange={e=>setIdB(e.target.value)}
              style={{width:"100%",padding:"10px 14px",border:`1.5px solid ${C.border}`,borderRadius:8,fontSize:13,color:C.body}}>
              <option value="">Select contract...</option>
              {allContracts.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>
        </div>
        <div style={{marginTop:16,display:"flex",gap:10}}>
          <button onClick={compare} disabled={!idA||!idB||idA===idB||loading}
            style={{padding:"10px 24px",background:!idA||!idB||idA===idB?"#D1D5DB":C.primary,
              color:"white",border:"none",borderRadius:8,fontSize:14,fontWeight:600,
              cursor:!idA||!idB||idA===idB?"not-allowed":"pointer"}}>
            {loading?"Comparing...":"Compare →"}
          </button>
          {idA===idB && idA && <span style={{fontSize:13,color:C.error,paddingTop:10}}>Select two different contracts</span>}
        </div>
      </div>

      {/* Comparison results */}
      {contractA && contractB && (
        <>
          {/* Header row */}
          <div style={{display:"grid",gridTemplateColumns:"200px 1fr 1fr",gap:0,marginBottom:20}}>
            <div/>
            {[contractA,contractB].map((c,i)=>(
              <div key={i} style={{background:i===0?C.primaryLight:"#FFF7ED",
                border:`1.5px solid ${i===0?"#C7D2FE":"#FDE68A"}`,
                borderRadius:12,padding:20,margin:"0 8px"}}>
                <div style={{fontSize:16,fontWeight:800,color:C.heading,marginBottom:4}}>{c.title}</div>
                <div style={{fontSize:13,color:C.muted}}>{c.counterparty||"—"}</div>
                <div style={{marginTop:10}}>
                  <RiskBadge level={c.risk_level||""}/>
                  {c.risk_score!==null && <span style={{fontSize:12,color:C.muted,marginLeft:8}}>Score: {Math.round(c.risk_score)}</span>}
                </div>
              </div>
            ))}
          </div>

          {/* Fields comparison */}
          <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden",marginBottom:20}}>
            <div style={{padding:"12px 20px",background:C.bg,borderBottom:`1px solid ${C.border}`,fontSize:13,fontWeight:700,color:C.heading}}>
              Key Terms
            </div>
            {fieldsToCompare.map(field=>{
              const valA = field.fmt ? field.fmt((contractA as any)[field.keyA], contractA) : (contractA as any)[field.keyA]||"—";
              const valB = field.fmt ? field.fmt((contractB as any)[field.keyB], contractB) : (contractB as any)[field.keyB]||"—";
              const diff = isDifferent(valA,valB);
              return (
                <div key={field.label} style={{display:"grid",gridTemplateColumns:"200px 1fr 1fr",
                  borderBottom:`1px solid ${C.border}`,
                  background:diff?"#FFFBEB":C.surface}}>
                  <div style={{padding:"12px 20px",fontSize:13,fontWeight:600,color:C.muted,display:"flex",alignItems:"center",gap:6}}>
                    {diff && <span style={{color:C.warning,fontSize:16}}>⚠</span>}
                    {field.label}
                  </div>
                  {[valA,valB].map((val,i)=>(
                    <div key={i} style={{padding:"12px 20px",fontSize:13,fontWeight:500,color:C.body,
                      borderLeft:`1px solid ${C.border}`,
                      background:diff?(i===0?"#FFF7ED20":"#FFF7ED40"):"transparent"}}>
                      {field.keyA==="risk_level" ? <RiskBadge level={String(val)}/> : String(val)}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>

          {/* Clause-by-clause comparison */}
          {allClauseTypes.length > 0 && (
            <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:12,overflow:"hidden"}}>
              <div style={{padding:"12px 20px",background:C.bg,borderBottom:`1px solid ${C.border}`,fontSize:13,fontWeight:700,color:C.heading}}>
                Clause Comparison ({allClauseTypes.length} types)
              </div>
              {allClauseTypes.map(type=>{
                const clA = getClause(contractA, type);
                const clB = getClause(contractB, type);
                const riskDiff = clA && clB && clA.risk_level !== clB.risk_level;
                return (
                  <div key={type} style={{display:"grid",gridTemplateColumns:"200px 1fr 1fr",
                    borderBottom:`1px solid ${C.border}`,
                    background:riskDiff?"#FFF7EB":C.surface}}>
                    <div style={{padding:"14px 20px",display:"flex",alignItems:"flex-start",gap:6}}>
                      {riskDiff && <span style={{color:C.warning,marginTop:2}}>⚠</span>}
                      <div>
                        <div style={{fontSize:12,fontWeight:700,color:C.primary,textTransform:"uppercase",letterSpacing:"0.04em"}}>
                          {type.replace(/_/g," ")}
                        </div>
                      </div>
                    </div>
                    {[clA,clB].map((cl,i)=>(
                      <div key={i} style={{padding:"14px 20px",borderLeft:`1px solid ${C.border}`}}>
                        {cl ? (
                          <>
                            <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:6}}>
                              <RiskBadge level={cl.risk_level}/>
                              {cl.section_reference && <span style={{fontSize:11,color:C.muted}}>{cl.section_reference}</span>}
                            </div>
                            <p style={{fontSize:13,color:C.body,lineHeight:1.5,margin:0}}>{cl.summary||cl.title||"—"}</p>
                          </>
                        ) : (
                          <span style={{fontSize:13,color:"#D1D5DB",fontStyle:"italic"}}>Not present</span>
                        )}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
