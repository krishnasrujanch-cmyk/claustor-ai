"use client";
import React from "react";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  Zap, Bot, Link2, Globe, FileSearch, Shield, Upload, Cpu,
  CheckSquare, Lock, Server, FileCheck, Key, ClipboardList,
  BarChart2, GitMerge, AlertTriangle, Languages, Download,
  ArrowRight, ChevronRight,
} from "lucide-react";

const C = {
  primary:"#0066FF", primaryHover:"#0052CC", primaryLight:"#E6F0FF",
  accent:"#00A3FF", navy:"#0A1128",
  heading:"#0F172A", body:"#334155", muted:"#475569",
  border:"#E2E8F0", surface:"#FFFFFF", bg:"#F8FAFC",
  success:"#22C55E", warning:"#F59E0B", error:"#EF4444",
};

// ── Claustor SVG Logo (from brand description) ────────────────────────────────
function ClauStorLogo({ size=40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none">
      <path d="M28 8C24.5 5.5 20 4 15 4C8.4 4 3 9.4 3 18s5.4 14 12 14c5 0 9.5-1.5 13-4"
        stroke="url(#logoGrad)" strokeWidth="3.5" strokeLinecap="round" fill="none"/>
      <circle cx="28" cy="8" r="2.5" fill={C.accent}/>
      <circle cx="28" cy="28" r="2.5" fill={C.accent}/>
      <line x1="28" y1="8" x2="33" y2="8" stroke={C.accent} strokeWidth="1.5"/>
      <circle cx="33" cy="8" r="1.5" fill={C.accent}/>
      <line x1="28" y1="28" x2="33" y2="28" stroke={C.accent} strokeWidth="1.5"/>
      <circle cx="33" cy="28" r="1.5" fill={C.accent}/>
      <rect x="11" y="11" width="11" height="14" rx="1.5"
        fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.25)" strokeWidth="0.75"/>
      <line x1="13" y1="15" x2="20" y2="15" stroke="rgba(255,255,255,0.5)" strokeWidth="0.75"/>
      <line x1="13" y1="18" x2="20" y2="18" stroke="rgba(255,255,255,0.5)" strokeWidth="0.75"/>
      <line x1="13" y1="21" x2="18" y2="21" stroke={C.accent} strokeWidth="1"/>
      <defs>
        <linearGradient id="logoGrad" x1="3" y1="4" x2="28" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor={C.primary}/>
          <stop offset="100%" stopColor={C.accent}/>
        </linearGradient>
      </defs>
    </svg>
  );
}

function ClauStorLogoLight({ size=40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none">
      <path d="M28 8C24.5 5.5 20 4 15 4C8.4 4 3 9.4 3 18s5.4 14 12 14c5 0 9.5-1.5 13-4"
        stroke="url(#logoGradLight)" strokeWidth="3.5" strokeLinecap="round" fill="none"/>
      <circle cx="28" cy="8" r="2.5" fill={C.accent}/>
      <circle cx="28" cy="28" r="2.5" fill={C.accent}/>
      <line x1="28" y1="8" x2="33" y2="8" stroke={C.accent} strokeWidth="1.5"/>
      <circle cx="33" cy="8" r="1.5" fill={C.accent}/>
      <line x1="28" y1="28" x2="33" y2="28" stroke={C.accent} strokeWidth="1.5"/>
      <circle cx="33" cy="28" r="1.5" fill={C.accent}/>
      <rect x="11" y="11" width="11" height="14" rx="1.5"
        fill={`${C.primary}08`} stroke={`${C.primary}30`} strokeWidth="0.75"/>
      <line x1="13" y1="15" x2="20" y2="15" stroke={`${C.primary}60`} strokeWidth="0.75"/>
      <line x1="13" y1="18" x2="20" y2="18" stroke={`${C.primary}60`} strokeWidth="0.75"/>
      <line x1="13" y1="21" x2="18" y2="21" stroke={C.accent} strokeWidth="1"/>
      <defs>
        <linearGradient id="logoGradLight" x1="3" y1="4" x2="28" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor={C.primary}/>
          <stop offset="100%" stopColor={C.accent}/>
        </linearGradient>
      </defs>
    </svg>
  );
}

// ── Animated counter ──────────────────────────────────────────────────────────
function Counter({ target, suffix="" }: { target:number; suffix?:string }) {
  const [val, setVal] = useState(0);
  const started = useRef(false);
  useEffect(()=>{
    if (started.current) return;
    started.current = true;
    const step = target / 60;
    let current = 0;
    const timer = setInterval(()=>{
      current = Math.min(current + step, target);
      setVal(Math.floor(current));
      if (current >= target) clearInterval(timer);
    }, 16);
    return ()=>clearInterval(timer);
  },[target]);
  return <>{val.toLocaleString()}{suffix}</>;
}

// ── Dashboard Preview (actual dashboard UI mock) ─────────────────────────────
function DashboardPreview() {
  const [activeCard, setActiveCard] = useState<string|null>(null);
  return (
    <div style={{
      width:"100%", maxWidth:1000, margin:"0 auto",
      borderRadius:16, overflow:"hidden",
      border:"1px solid rgba(0,102,255,0.12)",
      boxShadow:`0 25px 50px -12px rgba(0,102,255,0.12), 0 8px 32px rgba(0,0,0,0.08)`,
      background:"#F8FAFC", display:"flex",
    }}>
      {/* Sidebar mock */}
      <div style={{width:56,background:"#0A1128",display:"flex",
        flexDirection:"column",alignItems:"center",padding:"16px 0",gap:16,flexShrink:0}}>
        <div style={{width:32,height:32,borderRadius:8,
          background:"linear-gradient(135deg,#0066FF,#00A3FF)",
          display:"flex",alignItems:"center",justifyContent:"center",
          fontSize:14,fontWeight:900,color:"white"}}>C</div>
        {["◻","📄","✦","✓","📊"].map((icon,i)=>(
          <div key={i} style={{width:32,height:32,borderRadius:8,
            background:i===0?"rgba(0,102,255,0.2)":"transparent",
            display:"flex",alignItems:"center",justifyContent:"center",
            fontSize:14,color:i===0?"white":"rgba(255,255,255,0.3)"}}>
            {icon}
          </div>
        ))}
      </div>

      {/* Main content */}
      <div style={{flex:1,overflow:"hidden"}}>
        {/* Top bar */}
        <div style={{height:48,background:"white",borderBottom:"1px solid #E2E8F0",
          display:"flex",alignItems:"center",justifyContent:"space-between",
          padding:"0 20px"}}>
          <div style={{fontSize:14,fontWeight:700,color:"#111827"}}>Dashboard</div>
          <div style={{display:"flex",gap:8,alignItems:"center"}}>
            <div style={{width:24,height:24,borderRadius:"50%",
              background:"linear-gradient(135deg,#0066FF,#00A3FF)",
              display:"flex",alignItems:"center",justifyContent:"center",
              fontSize:10,fontWeight:700,color:"white"}}>D</div>
          </div>
        </div>

        {/* Dashboard content */}
        <div style={{padding:16}}>
          {/* Stats row */}
          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:12}}>
            {[
              {label:"Total Contracts", value:"24",   color:"#0066FF"},
              {label:"High Risk",       value:"3",    color:"#EF4444"},
              {label:"Pending Review",  value:"5",    color:"#F59E0B"},
              {label:"Analyzed Today",  value:"12",   color:"#22C55E"},
            ].map(s=>(
              <div key={s.label} style={{background:"white",borderRadius:8,padding:"10px 12px",
                border:"1px solid #E2E8F0"}}>
                <div style={{fontSize:9,color:"#94A3B8",marginBottom:4,textTransform:"uppercase",
                  letterSpacing:"0.06em"}}>{s.label}</div>
                <div style={{fontSize:20,fontWeight:900,color:s.color}}>{s.value}</div>
              </div>
            ))}
          </div>

          {/* Two column layout */}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
            {/* Recent contracts */}
            <div style={{background:"white",borderRadius:8,padding:12,border:"1px solid #E2E8F0"}}>
              <div style={{fontSize:11,fontWeight:700,color:"#111827",marginBottom:10}}>
                Recent Contracts
              </div>
              {[
                {title:"Pharma License Agreement",   risk:"high",   status:"analyzed"},
                {title:"IT Outsourcing MSA",          risk:"medium", status:"in_review"},
                {title:"Freelance Services Agreement",risk:"low",    status:"analyzed"},
                {title:"DKU Technologies Firm Reg",   risk:"low",    status:"pending"},
              ].map((c,i)=>(
                <div key={i}
                  onClick={()=>setActiveCard(c.title)}
                  style={{display:"flex",alignItems:"center",gap:8,padding:"7px 0",
                    borderBottom:i<3?"1px solid #F1F5F9":"none",cursor:"pointer"}}>
                  <div style={{width:4,height:28,borderRadius:2,flexShrink:0,
                    background:c.risk==="high"?"#EF4444":c.risk==="medium"?"#F59E0B":"#22C55E"}}/>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontSize:11,fontWeight:600,color:"#111827",
                      overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                      {c.title}
                    </div>
                    <div style={{fontSize:9,color:"#94A3B8",textTransform:"capitalize"}}>
                      {c.status.replace("_"," ")}
                    </div>
                  </div>
                  <span style={{fontSize:9,fontWeight:700,padding:"2px 6px",borderRadius:20,
                    background:c.risk==="high"?"#FEF2F2":c.risk==="medium"?"#FFFBEB":"#F0FDF4",
                    color:c.risk==="high"?"#DC2626":c.risk==="medium"?"#D97706":"#16A34A",
                    whiteSpace:"nowrap"}}>
                    {c.risk.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>

            {/* AI Copilot panel */}
            <div style={{background:"white",borderRadius:8,padding:12,
              border:`1px solid ${activeCard?"#0066FF30":"#E2E8F0"}`,
              transition:"border-color 0.2s"}}>
              <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:10}}>
                <div style={{width:20,height:20,borderRadius:"50%",flexShrink:0,
                  background:`conic-gradient(from 0deg,#0066FF,#00A3FF,#A855F7)`,
                  display:"flex",alignItems:"center",justifyContent:"center",
                  fontSize:9,fontWeight:800,color:"white"}}>✦</div>
                <span style={{fontSize:11,fontWeight:700,color:"#111827"}}>AI Copilot</span>
                {activeCard && (
                  <span style={{fontSize:8,padding:"1px 6px",borderRadius:20,
                    background:"#E6F0FF",color:"#0066FF",fontWeight:600,marginLeft:"auto",
                    overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:100}}>
                    {activeCard.split(" ").slice(0,2).join(" ")} ▾
                  </span>
                )}
              </div>
              {activeCard ? (
                <>
                  <div style={{background:"#F8FAFF",borderRadius:6,padding:"8px 10px",
                    fontSize:10,color:"#334155",lineHeight:1.5,marginBottom:8}}>
                    <strong>IP Ownership clause</strong> grants Licensor permanent ownership
                    of all inventions. Risk score: <span style={{color:"#DC2626",fontWeight:700}}>95/100 HIGH</span>.
                    <div style={{marginTop:4,display:"flex",gap:4}}>
                      <span style={{fontSize:8,padding:"1px 5px",borderRadius:20,
                        background:"#E6F0FF",color:"#0066FF",fontWeight:600}}>[1] §4.1</span>
                      <span style={{fontSize:8,padding:"1px 5px",borderRadius:20,
                        background:"#E6F0FF",color:"#0066FF",fontWeight:600}}>[2] §4.3</span>
                    </div>
                  </div>
                  {["What royalties are owed?","Can this be negotiated?"].map(q=>(
                    <div key={q} style={{padding:"4px 8px",border:"1px solid #E6F0FF",
                      borderRadius:20,fontSize:9,color:"#0066FF",marginBottom:4,
                      background:"#E6F0FF",cursor:"pointer",fontWeight:500}}>
                      {q}
                    </div>
                  ))}
                </>
              ) : (
                <div style={{textAlign:"center",padding:"16px 0",color:"#94A3B8"}}>
                  <div style={{fontSize:18,marginBottom:4}}>✦</div>
                  <div style={{fontSize:10}}>Click a contract to ask AI</div>
                </div>
              )}
              <div style={{marginTop:8,display:"flex",gap:0,
                border:"1px solid #E2E8F0",borderRadius:8,overflow:"hidden"}}>
                <input readOnly placeholder="Ask about your contracts..."
                  style={{flex:1,padding:"7px 10px",border:"none",fontSize:10,
                    color:"#94A3B8",background:"transparent",outline:"none"}}/>
                <div style={{padding:"0 10px",background:"#0066FF",
                  display:"flex",alignItems:"center"}}>
                  <span style={{color:"white",fontSize:10}}>→</span>
                </div>
              </div>
            </div>

            {/* Risk chart mock */}
            <div style={{background:"white",borderRadius:8,padding:12,border:"1px solid #E2E8F0"}}>
              <div style={{fontSize:11,fontWeight:700,color:"#111827",marginBottom:10}}>
                Risk Distribution
              </div>
              <div style={{display:"flex",gap:8,alignItems:"flex-end",height:60,marginBottom:8}}>
                {[
                  {label:"Low",   pct:60, color:"#22C55E"},
                  {label:"Med",   pct:25, color:"#F59E0B"},
                  {label:"High",  pct:15, color:"#EF4444"},
                ].map(b=>(
                  <div key={b.label} style={{flex:1,display:"flex",
                    flexDirection:"column",alignItems:"center",gap:4}}>
                    <div style={{width:"100%",borderRadius:"3px 3px 0 0",
                      background:b.color,height:`${b.pct*0.6}px`}}/>
                    <div style={{fontSize:9,color:"#94A3B8"}}>{b.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Obligations */}
            <div style={{background:"white",borderRadius:8,padding:12,border:"1px solid #E2E8F0"}}>
              <div style={{fontSize:11,fontWeight:700,color:"#111827",marginBottom:10}}>
                Upcoming Obligations
              </div>
              {[
                {title:"Final Delivery Payment", days:15, amount:"₹8,50,000"},
                {title:"Contract Renewal Notice", days:30, amount:"—"},
                {title:"SLA Review Meeting",      days:45, amount:"—"},
              ].map((o,i)=>(
                <div key={i} style={{display:"flex",alignItems:"center",gap:8,
                  padding:"5px 0",borderBottom:i<2?"1px solid #F1F5F9":"none"}}>
                  <div style={{width:28,height:28,borderRadius:6,flexShrink:0,
                    background:o.days<=15?"#FEF2F2":o.days<=30?"#FFFBEB":"#F8FAFC",
                    display:"flex",alignItems:"center",justifyContent:"center",
                    fontSize:9,fontWeight:700,
                    color:o.days<=15?"#DC2626":o.days<=30?"#D97706":"#64748B"}}>
                    {o.days}d
                  </div>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontSize:10,fontWeight:600,color:"#111827",
                      overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                      {o.title}
                    </div>
                    {o.amount!=="—"&&<div style={{fontSize:9,color:"#94A3B8"}}>{o.amount}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


// ── Bento feature grid ────────────────────────────────────────────────────────
const FEATURES = [
  {Icon:Zap,       title:"Risk Scoring 0-100",        hero:true,
   desc:"Real-time risk engine across 25+ clause types. Industry weights: Healthcare data_protection 2×, Tech IP 2×. Full 0-100 range — never clusters around 30.",
   gradient:`linear-gradient(135deg,${C.primary}08,${C.accent}08)`},
  {Icon:Bot,       title:"AI Copilot",                hero:true,
   desc:"Categorised prompt library (Risk/Financial/Legal/IP). Follow-up suggestions. Cited responses with clause references. Rejection banner for flagged contracts.",
   gradient:`linear-gradient(135deg,#8B5CF608,${C.primary}08)`},
  {Icon:FileSearch,title:"Hybrid Clause Detection",   hero:false,
   desc:"Regex pre-segments → LLM classifies. 25 clause types."},
  {Icon:Link2,     title:"Clause Relationships",      hero:false,
   desc:"Auto-maps payment→termination→SLA cross-references."},
  {Icon:Languages, title:"Multi-language",             hero:false,
   desc:"EN/HI/FR/DE/ES detection. Clause extraction adapts."},
  {Icon:AlertTriangle,title:"Missing Clause Detection",hero:false,
   desc:"Flags expected clauses not found by contract type."},
  {Icon:GitMerge,  title:"Playbook Similarity",        hero:false,
   desc:"Compare clauses against your standard templates."},
  {Icon:ClipboardList,title:"Audit Log",              hero:false,
   desc:"Full event trail. Data export (GDPR Art. 20)."},
  {Icon:Download,  title:"Data Export",               hero:false,
   desc:"ZIP with contracts, clauses, obligations, audit CSV."},
];

const STEPS = [
  {Icon:Upload,      title:"Upload",      step:1,
   desc:"PDF, DOCX, Excel, XML. OCR for scanned documents.",    hero:false},
  {Icon:Cpu,         title:"AI Analysis", step:2,
   desc:"Extracts clauses, scores risks, maps relationships — in under 60s.", hero:true},
  {Icon:CheckSquare, title:"Review & Act",step:3,
   desc:"Clause-by-clause review. AI answers any question with citations.", hero:false},
];

const INDUSTRIES = [
  {icon:"💊",name:"Pharma"},    {icon:"🏦",name:"BFSI"},
  {icon:"💻",name:"IT/SaaS"},   {icon:"🏥",name:"Healthcare"},
  {icon:"🏭",name:"Manufacturing"},{icon:"🛒",name:"Retail"},
  {icon:"⚡",name:"Energy"},    {icon:"⚖️",name:"Legal"},
];

const PLANS = [
  {id:"free",        label:"Free",         price:"₹0",    period:"forever",
   features:["5 contracts","100 AI queries","1 user","General analysis"],
   cta:"Start free", href:"/register"},
  {id:"starter",     label:"Starter",      price:"₹3,999", period:"/mo + GST",
   features:[
     "100 contracts/month",
     "5,000 AI queries/month",
     "5 users",
     "PDF/DOCX/Excel/XML",
     "OCR for scanned PDFs",
     "Obligation tracking",
     "Review workflow",
     "Audit log",
     "Data export",
   ],
   addon:"+ ₹1,000/mo Industry Pack",
   addonFeatures:[
     "IT/SaaS industry scoring",
     "Manufacturing scoring",
     "HR/Employment scoring",
     "Industry clause priorities",
   ],
   cta:"Start Starter", href:"/register?plan=starter"},
  {id:"professional",label:"Professional", price:"₹16,499",period:"/mo + GST",
   popular:true,
   features:[
     "1,000 contracts/month",
     "50,000 AI queries/month",
     "25 users",
     "All file formats + OCR",
     "Bulk import",
     "Review workflow",
     "Webhooks & API access",
     "Dedicated processing queue",
     "PII masking (Presidio AI)",
     "25 clause types",
     "Risk scoring 0-100",
     "Playbook similarity",
     "Industry risk weights",
     "Missing clause detection",
     "Clause relationships",
     "Language detection (5 lang)",
     "Image recognition (OCR+AI)",
     "Org-level isolation",
     "AES-256 encryption",
     "Audit log + data export",
     "GDPR data portability",
     "India data residency",
   ],
   addon:"+ ₹2,500/mo Pro Industry Pack (all 8 industries)",
   addonFeatures:[
     "All 8 industry playbooks (Pharma, BFSI, Tech, Healthcare, Manufacturing, Retail, Energy, Legal)",
     "Custom clause weights per industry",
     "Priority industry processing queue",
     "Dedicated industry playbooks",
     "2× risk weight for critical industry clauses",
   ],
   cta:"Start Professional", href:"/register?plan=professional"},
  {id:"enterprise",  label:"Enterprise",   price:"Custom", period:"",
   features:["Unlimited contracts","Unlimited users","SSO/SAML","On-premise",
             "SOC2 report","Custom taxonomy","Dedicated CSM"],
   cta:"Contact Sales", href:"mailto:hello@claustor.ai"},
];

const TRUST = [
  {Icon:Lock,        label:"AES-256 Encryption",    desc:"All data encrypted at rest and in transit"},
  {Icon:Server,      label:"SOC2 Infrastructure",   desc:"Hosted on SOC2-compliant cloud providers"},
  {Icon:Globe,       label:"India Data Residency",  desc:"Data stored in Mumbai (asia-south1)"},
  {Icon:FileCheck,   label:"GDPR Compliant",        desc:"Full data portability and deletion rights"},
  {Icon:Key,         label:"Org-level Isolation",   desc:"Zero cross-tenant data access possible"},
  {Icon:ClipboardList,label:"Full Audit Trail",     desc:"Every access logged and exportable"},
];

export default function LandingPage() {
  const [scrolled, setScrolled]         = useState(false);
  const [activeIndustry, setActiveIndustry] = useState(0);
  const [expandedAddon, setExpandedAddon] = useState<string|null>(null);
  const [addonSelected, setAddonSelected] = useState<Set<string>>(new Set());

  useEffect(()=>{
    const h = ()=>setScrolled(window.scrollY>20);
    window.addEventListener("scroll",h);
    return ()=>window.removeEventListener("scroll",h);
  },[]);

  return (
    <div style={{fontFamily:"Inter,system-ui,sans-serif",color:C.body,background:C.surface}}>

      {/* ── Sticky Nav ─────────────────────────────────────────────────────── */}
      <nav style={{
        position:"sticky",top:0,zIndex:100,
        background:scrolled?"rgba(255,255,255,0.92)":"transparent",
        backdropFilter:scrolled?"blur(12px)":"none",
        borderBottom:`1px solid ${scrolled?C.border:"transparent"}`,
        transition:"all 0.3s",padding:"0 48px",
      }}>
        <div style={{maxWidth:1200,margin:"0 auto",display:"flex",
          alignItems:"center",height:64,gap:32}}>
          <Link href="/" style={{textDecoration:"none",
            display:"flex",alignItems:"center",gap:10}}>
            <ClauStorLogoLight size={36}/>
            <div>
              <div style={{fontWeight:800,fontSize:18,color:C.heading,
                letterSpacing:"-0.01em",lineHeight:1}}>
                <span style={{color:C.accent}}>C</span>laustor
              </div>
              <div style={{fontSize:8,color:C.muted,letterSpacing:"0.06em"}}>
                AI Contract Intelligence
              </div>
            </div>
          </Link>
          <div style={{display:"flex",gap:24,flex:1}}>
            {["Features","Pricing","Security","Industries"].map(l=>(
              <a key={l} href={`#${l.toLowerCase()}`}
                style={{fontSize:14,color:C.muted,textDecoration:"none",
                  fontWeight:500,transition:"color 0.15s"}}
                onMouseEnter={e=>(e.currentTarget as HTMLElement).style.color=C.heading}
                onMouseLeave={e=>(e.currentTarget as HTMLElement).style.color=C.muted}>
                {l}
              </a>
            ))}
          </div>
          <div style={{display:"flex",gap:10,alignItems:"center"}}>
            <Link href="/login"
              style={{fontSize:14,color:C.muted,textDecoration:"none",
                fontWeight:500,padding:"6px 14px"}}>
              Sign in
            </Link>
            <Link href="/register"
              style={{padding:"8px 20px",background:C.primary,color:"white",
                borderRadius:8,fontSize:14,fontWeight:700,textDecoration:"none",
                boxShadow:`0 2px 8px ${C.primary}40`,transition:"all 0.2s"}}
              onMouseEnter={e=>(e.currentTarget as HTMLElement).style.background=C.primaryHover}
              onMouseLeave={e=>(e.currentTarget as HTMLElement).style.background=C.primary}>
              Start free
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <section style={{
        background:`radial-gradient(ellipse at 50% -20%,rgba(0,102,255,0.07) 0%,transparent 60%)`,
        padding:"80px 48px 60px",textAlign:"center",
      }}>
        <div style={{maxWidth:720,margin:"0 auto"}}>
          {/* Subtle AI badge */}
          <div style={{display:"inline-flex",alignItems:"center",gap:6,
            padding:"5px 14px",borderRadius:20,marginBottom:32,
            background:C.primaryLight,border:`1px solid ${C.primary}15`}}>
            <span style={{fontSize:11,fontWeight:700,color:C.primary}}>
              ✦ AI-Powered Contract Intelligence
            </span>
          </div>

          <h1 style={{fontSize:52,fontWeight:900,color:C.heading,
            lineHeight:1.1,letterSpacing:"-0.03em",marginBottom:20}}>
            Your contracts,{" "}
            <span style={{background:`linear-gradient(135deg,${C.primary},${C.accent})`,
              WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>
              understood
            </span>
            {" "}in seconds
          </h1>

          <p style={{fontSize:18,color:C.body,lineHeight:1.7,
            marginBottom:32,maxWidth:560,margin:"0 auto 32px"}}>
            Upload any PDF or DOCX. Claustor extracts every clause, scores every risk,
            and answers any question — with citations from the actual contract.
          </p>

          <div style={{display:"flex",gap:12,justifyContent:"center",
            flexWrap:"wrap",marginBottom:16}}>
            <Link href="/register"
              style={{padding:"14px 28px",background:C.primary,color:"white",
                borderRadius:10,fontSize:16,fontWeight:700,textDecoration:"none",
                boxShadow:`0 4px 16px ${C.primary}40`,
                display:"flex",alignItems:"center",gap:8}}>
              Start free — no card required
              <ArrowRight size={16}/>
            </Link>
            <a href="#features"
              style={{padding:"14px 28px",background:"transparent",color:C.heading,
                border:`1.5px solid ${C.border}`,borderRadius:10,fontSize:16,
                fontWeight:600,textDecoration:"none",transition:"all 0.2s"}}
              onMouseEnter={e=>{
                (e.currentTarget as HTMLElement).style.borderColor=C.primary;
                (e.currentTarget as HTMLElement).style.color=C.primary;
              }}
              onMouseLeave={e=>{
                (e.currentTarget as HTMLElement).style.borderColor=C.border;
                (e.currentTarget as HTMLElement).style.color=C.heading;
              }}>
              ⏯ See how it works
            </a>
          </div>
          <p style={{fontSize:12,color:C.muted}}>
            Free forever · No credit card · 5 contracts included
          </p>
        </div>

        {/* Dashboard Preview */}
        <div style={{maxWidth:1000,margin:"48px auto 0",padding:"0 24px"}}>
          <DashboardPreview/>
        </div>
      </section>

      {/* ── Metrics ────────────────────────────────────────────────────────── */}
      <section style={{background:C.bg,borderTop:`1px solid ${C.border}`,
        borderBottom:`1px solid ${C.border}`,padding:"40px 48px"}}>
        <div style={{maxWidth:1100,margin:"0 auto",
          display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:24}}>
          {[
            {Icon:Zap,   value:50000,suffix:"+", label:"Contracts analyzed",    sub:"< 60s each"},
            {Icon:FileSearch,value:94,suffix:"%",label:"Clause accuracy",        sub:"across 25 types"},
            {Icon:Bot,   value:8,   suffix:"×",  label:"Faster than manual",     sub:"legal team productivity"},
            {Icon:Shield,value:100, suffix:"%",  label:"Data isolation",          sub:"zero cross-tenant access"},
          ].map(m=>(
            <div key={m.label} style={{textAlign:"center",padding:"20px 16px",
              background:C.surface,borderRadius:12,border:`1px solid ${C.border}`,
              boxShadow:"0 1px 3px rgba(0,0,0,0.04)"}}>
              <div style={{width:36,height:36,borderRadius:8,margin:"0 auto 12px",
                background:C.primaryLight,display:"flex",alignItems:"center",justifyContent:"center"}}>
                <m.Icon size={16} style={{color:C.primary}}/>
              </div>
              <div style={{fontSize:30,fontWeight:900,color:C.primary,
                letterSpacing:"-0.02em",marginBottom:4}}>
                <Counter target={m.value} suffix={m.suffix}/>
              </div>
              <div style={{fontSize:13,fontWeight:600,color:C.heading,marginBottom:2}}>
                {m.label}
              </div>
              <div style={{fontSize:11,color:C.muted}}>{m.sub}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ───────────────────────────────────────────────────── */}
      <section id="features" style={{padding:"80px 48px",background:C.surface}}>
        <div style={{maxWidth:1100,margin:"0 auto"}}>
          <div style={{textAlign:"center",marginBottom:48}}>
            <div style={{fontSize:11,fontWeight:700,color:C.primary,
              letterSpacing:"0.1em",textTransform:"uppercase",marginBottom:8}}>
              How it works
            </div>
            <h2 style={{fontSize:36,fontWeight:800,color:C.heading,
              letterSpacing:"-0.02em"}}>
              From upload to insight in 3 steps
            </h2>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 48px 1fr 48px 1fr",
            alignItems:"start",gap:0}}>
            {STEPS.map((s,i)=>(
              <React.Fragment key={`step-${i}`}>
                <div style={{textAlign:"center",padding:"32px 24px",
                  background:s.hero?C.primaryLight:C.bg,borderRadius:16,
                  border:s.hero?`2px solid ${C.primary}`:`1px solid ${C.border}`,
                  position:"relative"}}>
                  {s.hero && (
                    <div style={{position:"absolute",top:-12,left:"50%",
                      transform:"translateX(-50%)",fontSize:9,fontWeight:700,
                      padding:"3px 12px",background:C.primary,color:"white",
                      borderRadius:20,whiteSpace:"nowrap",letterSpacing:"0.06em"}}>
                      ⚡ CORE AI ENGINE
                    </div>
                  )}
                  <div style={{width:52,height:52,borderRadius:"50%",margin:"0 auto 16px",
                    background:s.hero?`${C.primary}15`:C.surface,
                    border:`2px solid ${s.hero?C.primary:C.border}`,
                    display:"flex",alignItems:"center",justifyContent:"center"}}>
                    <s.Icon size={20} style={{color:s.hero?C.primary:C.muted}}/>
                  </div>
                  <div style={{fontSize:10,fontWeight:700,color:C.primary,
                    marginBottom:6,textTransform:"uppercase",letterSpacing:"0.05em"}}>
                    Step {s.step}
                  </div>
                  <h3 style={{fontSize:17,fontWeight:700,color:C.heading,marginBottom:8}}>
                    {s.title}
                  </h3>
                  <p style={{fontSize:13,color:s.hero?C.primary:C.muted,lineHeight:1.6}}>
                    {s.desc}
                  </p>
                </div>
                {i < 2 && (
                  <div key={`arrow-${i}`} style={{display:"flex",alignItems:"center",
                    justifyContent:"center",paddingTop:60}}>
                    <div style={{width:24,height:2,background:C.border,position:"relative"}}>
                      <ChevronRight size={14} style={{color:C.muted,
                        position:"absolute",right:-7,top:-6}}/>
                    </div>
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </section>

      {/* ── Bento Feature Grid ──────────────────────────────────────────────── */}
      <section style={{padding:"80px 48px",background:C.bg}}>
        <div style={{maxWidth:1100,margin:"0 auto"}}>
          <div style={{textAlign:"center",marginBottom:48}}>
            <h2 style={{fontSize:36,fontWeight:800,color:C.heading,
              letterSpacing:"-0.02em",marginBottom:12}}>
              Everything your legal team needs
            </h2>
            <p style={{fontSize:16,color:C.muted}}>
              25 clause types · Playbook scoring · Industry weights · Full audit trail
            </p>
          </div>

          {/* Bento grid */}
          <div style={{display:"grid",
            gridTemplateColumns:"1fr 1fr 1fr",
            gridTemplateRows:"auto auto auto",
            gap:16}}>

            {/* Hero card 1 — Risk Scoring (spans 2 cols) */}
            <div style={{gridColumn:"1/3",padding:28,borderRadius:14,
              background:`linear-gradient(135deg,${C.primary}08,${C.accent}05)`,
              border:`1px solid ${C.primary}20`,
              transition:"all 0.15s"}}
              onMouseEnter={e=>{(e.currentTarget as HTMLElement).style.borderColor=C.primary;
                (e.currentTarget as HTMLElement).style.boxShadow=`0 4px 20px ${C.primary}15`;}}
              onMouseLeave={e=>{(e.currentTarget as HTMLElement).style.borderColor=`${C.primary}20`;
                (e.currentTarget as HTMLElement).style.boxShadow="none";}}>
              <div style={{width:44,height:44,borderRadius:10,marginBottom:16,
                background:C.primaryLight,display:"flex",alignItems:"center",justifyContent:"center"}}>
                <Zap size={22} style={{color:C.primary}}/>
              </div>
              <h3 style={{fontSize:18,fontWeight:700,color:C.heading,marginBottom:8}}>
                Risk Scoring 0-100
              </h3>
              <p style={{fontSize:14,color:C.muted,lineHeight:1.6,marginBottom:16}}>
                Real-time risk engine across 25+ clause types with custom industry weights.
                Healthcare data_protection 2×, Tech IP ownership 2×.
                Full 0-100 range — never clusters around a single value.
              </p>
              <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
                {["Payment","Liability","IP Ownership","Termination","SLA","Indemnification"].map(t=>(
                  <span key={t} style={{fontSize:11,fontWeight:600,padding:"3px 10px",
                    borderRadius:20,background:C.primaryLight,color:C.primary}}>
                    {t}
                  </span>
                ))}
              </div>
            </div>

            {/* Hero card 2 — AI Copilot */}
            <div style={{gridColumn:"3/4",gridRow:"1/3",padding:28,borderRadius:14,
              background:`linear-gradient(135deg,#8B5CF608,${C.primary}05)`,
              border:"1px solid #8B5CF620",
              transition:"all 0.15s"}}
              onMouseEnter={e=>{(e.currentTarget as HTMLElement).style.borderColor="#8B5CF6";
                (e.currentTarget as HTMLElement).style.boxShadow="0 4px 20px #8B5CF615";}}
              onMouseLeave={e=>{(e.currentTarget as HTMLElement).style.borderColor="#8B5CF620";
                (e.currentTarget as HTMLElement).style.boxShadow="none";}}>
              <div style={{width:44,height:44,borderRadius:10,marginBottom:16,
                background:"#F5F3FF",display:"flex",alignItems:"center",justifyContent:"center"}}>
                <Bot size={22} style={{color:"#7C3AED"}}/>
              </div>
              <h3 style={{fontSize:18,fontWeight:700,color:C.heading,marginBottom:8}}>
                AI Copilot
              </h3>
              <p style={{fontSize:13,color:C.muted,lineHeight:1.6,marginBottom:16}}>
                Categorised prompt library across Risk, Financial, Legal, and IP domains.
                Context-aware follow-up suggestions. Cited responses with clause references.
                Rejection banner for flagged contracts.
              </p>
              <div style={{background:C.surface,borderRadius:10,padding:12,
                border:"1px solid #E2E8F0",fontSize:11}}>
                <div style={{color:"#7C3AED",fontWeight:600,marginBottom:6}}>
                  🛡️ Risk Prompts
                </div>
                {["What is the liability cap?","Is indemnification capped?","What are the high-risk clauses?"].map(q=>(
                  <div key={q} style={{padding:"4px 0",borderBottom:"1px solid #F1F5F9",
                    color:C.muted,fontSize:10}}>{q}</div>
                ))}
              </div>
            </div>

            {/* Standard cards row */}
            {[
              {Icon:FileSearch, title:"Hybrid Detection",    desc:"Regex + LLM. 25 clause types."},
              {Icon:Link2,      title:"Clause Relationships",desc:"Payment→Termination→SLA cross-refs."},
              {Icon:Languages,  title:"Multi-language",       desc:"EN/HI/FR/DE/ES detection."},
              {Icon:AlertTriangle,title:"Missing Clauses",   desc:"Flags expected clauses not found."},
              {Icon:GitMerge,   title:"Playbook Match",      desc:"Compare against your templates."},
              {Icon:ClipboardList,title:"Audit + Export",    desc:"Full trail. GDPR data portability."},
            ].map(f=>(
              <div key={f.title} style={{padding:20,background:C.surface,
                borderRadius:12,border:`1px solid ${C.border}`,
                transition:"all 0.15s"}}
                onMouseEnter={e=>{(e.currentTarget as HTMLElement).style.borderColor=C.primary;
                  (e.currentTarget as HTMLElement).style.boxShadow=`0 4px 16px ${C.primary}10`;}}
                onMouseLeave={e=>{(e.currentTarget as HTMLElement).style.borderColor=C.border;
                  (e.currentTarget as HTMLElement).style.boxShadow="none";}}>
                <div style={{width:36,height:36,borderRadius:8,marginBottom:10,
                  background:C.primaryLight,display:"flex",alignItems:"center",justifyContent:"center"}}>
                  <f.Icon size={16} style={{color:C.primary}}/>
                </div>
                <h3 style={{fontSize:14,fontWeight:700,color:C.heading,marginBottom:4}}>
                  {f.title}
                </h3>
                <p style={{fontSize:12,color:C.muted,lineHeight:1.5}}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Industries ──────────────────────────────────────────────────────── */}
      <section id="industries" style={{padding:"80px 48px",background:C.surface}}>
        <div style={{maxWidth:1100,margin:"0 auto",textAlign:"center"}}>
          <div style={{fontSize:11,fontWeight:700,color:C.primary,
            letterSpacing:"0.1em",textTransform:"uppercase",marginBottom:8}}>
            Industry Intelligence
          </div>
          <h2 style={{fontSize:36,fontWeight:800,color:C.heading,
            letterSpacing:"-0.02em",marginBottom:12}}>
            Built for your industry's contracts
          </h2>
          <p style={{fontSize:16,color:C.muted,marginBottom:40}}>
            Industry-specific clause taxonomy, risk weights, and playbook templates as add-ons.
          </p>
          <div style={{display:"flex",gap:8,flexWrap:"wrap",justifyContent:"center"}}>
            {INDUSTRIES.map((ind,i)=>(
              <button key={ind.name} onClick={()=>setActiveIndustry(i)}
                style={{padding:"8px 16px",borderRadius:20,border:"none",
                  cursor:"pointer",fontSize:13,fontWeight:600,transition:"all 0.15s",
                  background:activeIndustry===i?C.primary:"#F1F5F9",
                  color:activeIndustry===i?"white":C.muted}}>
                {ind.icon} {ind.name}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ────────────────────────────────────────────────────────── */}
      <section id="pricing" style={{padding:"80px 48px",background:C.bg}}>
        <div style={{maxWidth:1100,margin:"0 auto"}}>
          <div style={{textAlign:"center",marginBottom:48}}>
            <h2 style={{fontSize:36,fontWeight:800,color:C.heading,
              letterSpacing:"-0.02em",marginBottom:12}}>
              Simple, transparent pricing
            </h2>
            <p style={{fontSize:16,color:C.muted}}>
              Start free. Scale as you grow. Industry packs as add-ons.
            </p>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:16}}>
            {PLANS.map(plan=>(
              <div key={plan.id} style={{
                background:plan.popular?C.navy:C.surface,
                color:plan.popular?"white":C.body,
                borderRadius:14,
                border:plan.popular?`2px solid ${C.primary}`:`1px solid ${C.border}`,
                boxShadow:plan.popular?`0 8px 32px ${C.primary}30`:"none",
                display:"flex",flexDirection:"column",
              }}>
                {/* Banner */}
                {plan.popular && (
                  <div style={{padding:"6px",textAlign:"center",
                    background:C.primary,fontSize:10,fontWeight:700,
                    color:"white",letterSpacing:"0.08em"}}>
                    ⭐ MOST POPULAR
                  </div>
                )}
                <div style={{padding:24,flex:1,display:"flex",flexDirection:"column",gap:16}}>
                  <div>
                    <div style={{fontSize:14,fontWeight:700,marginBottom:2,
                      color:plan.popular?"rgba(255,255,255,0.7)":C.muted}}>
                      {plan.label}
                    </div>
                    <div style={{fontSize:24,fontWeight:900,letterSpacing:"-0.02em",
                      color:plan.popular?"white":C.heading}}>
                      {addonSelected.has(plan.id) && (plan as any).addon
                        ? <>
                            {plan.id==="starter"?"₹4,999":
                             plan.id==="professional"?"₹18,999":plan.price}
                            <span style={{fontSize:11,fontWeight:400,
                              color:plan.popular?"rgba(255,255,255,0.5)":C.muted}}>
                              {plan.period}
                            </span>
                            <div style={{fontSize:10,color:C.success,fontWeight:600,marginTop:2}}>
                              incl. industry pack
                            </div>
                          </>
                        : <>{plan.price}
                            {plan.period&&<span style={{fontSize:11,fontWeight:400,
                              color:plan.popular?"rgba(255,255,255,0.5)":C.muted}}>
                              {plan.period}
                            </span>}
                          </>
                      }
                    </div>
                    {(plan as any).addon && (
                      <div style={{marginTop:6,position:"relative",zIndex:10}}>
                        <button
                          onClick={()=>setExpandedAddon(expandedAddon===plan.id?null:plan.id)}
                          style={{display:"flex",alignItems:"center",gap:4,
                            background:"none",border:"none",cursor:"pointer",padding:0,
                            fontSize:10,fontWeight:700,
                            color:plan.popular?"rgba(255,255,255,0.7)":C.warning}}>
                          🏭 Industry Pack Add-on
                          <span style={{fontSize:9}}>
                            {expandedAddon===plan.id?"▲":"▼"}
                          </span>
                        </button>
                        {expandedAddon===plan.id && (
                          <div style={{marginTop:6,padding:"8px 10px",borderRadius:8,
                            background:plan.popular?"rgba(255,255,255,0.08)":"#FFFBEB",
                            border:plan.popular?"1px solid rgba(255,255,255,0.1)":"1px solid #F59E0B30"}}>
                            <div style={{fontSize:11,fontWeight:700,marginBottom:4,
                              color:plan.popular?"white":C.warning}}>
                              {(plan as any).addon}
                            </div>
                            {((plan as any).addonFeatures||[]).map((f:string)=>(
                              <div key={f} style={{fontSize:10,
                                color:plan.popular?"rgba(255,255,255,0.6)":C.muted,
                                padding:"2px 0",display:"flex",alignItems:"center",gap:4}}>
                                <span style={{color:C.warning}}>✓</span> {f}
                              </div>
                            ))}
                            <button
                              onClick={()=>{
                                const s = new Set(addonSelected);
                                s.has(plan.id)?s.delete(plan.id):s.add(plan.id);
                                setAddonSelected(s);
                              }}
                              style={{display:"block",width:"100%",marginTop:8,
                                padding:"6px 12px",borderRadius:8,border:"none",
                                background:addonSelected.has(plan.id)?"#22C55E":C.warning,
                                color:"white",fontSize:10,fontWeight:700,
                                textAlign:"center",cursor:"pointer"}}>
                              {addonSelected.has(plan.id)?"✅ Added — Remove":"+ Add Industry Pack"}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <div style={{marginBottom:8}}>
                    {/* Always show first 3 */}
                    {plan.features.slice(0,3).map(f=>(
                      <div key={f} style={{display:"flex",gap:7,
                        alignItems:"flex-start",fontSize:12,marginBottom:5}}>
                        <CheckSquare size={11} style={{
                          color:plan.popular?"rgba(255,255,255,0.7)":C.success,
                          flexShrink:0,marginTop:1}}/>
                        <span style={{color:plan.popular?"rgba(255,255,255,0.85)":C.body}}>
                          {f}
                        </span>
                      </div>
                    ))}
                    {/* Collapsible rest */}
                    {expandedAddon===`feat-${plan.id}` && plan.features.slice(3).map(f=>(
                      <div key={f} style={{display:"flex",gap:7,
                        alignItems:"flex-start",fontSize:12,marginBottom:5}}>
                        <CheckSquare size={11} style={{
                          color:plan.popular?"rgba(255,255,255,0.7)":C.success,
                          flexShrink:0,marginTop:1}}/>
                        <span style={{color:plan.popular?"rgba(255,255,255,0.85)":C.body}}>
                          {f}
                        </span>
                      </div>
                    ))}
                    {plan.features.length > 3 && (
                      <button
                        onClick={()=>setExpandedAddon(
                          expandedAddon===`feat-${plan.id}`?null:`feat-${plan.id}`)}
                        style={{fontSize:11,fontWeight:600,background:"none",border:"none",
                          cursor:"pointer",padding:"4px 0",
                          color:plan.popular?"rgba(255,255,255,0.6)":C.primary,
                          display:"flex",alignItems:"center",gap:4}}>
                        {expandedAddon===`feat-${plan.id}`
                          ?"▲ Show less"
                          :`▼ +${plan.features.length-3} more features`}
                      </button>
                    )}
                  </div>
                  <Link href={addonSelected.has(plan.id)
                      ? plan.href+"&addon=industry"
                      : plan.href}
                    style={{
                      padding:"11px",borderRadius:8,fontSize:13,fontWeight:700,
                      textAlign:"center",textDecoration:"none",transition:"all 0.2s",
                      display:"block",
                      background:plan.popular?"white":"transparent",
                      color:plan.popular?C.primary:C.primary,
                      border:plan.popular?"none":`2px solid ${C.primary}`,
                    }}>
                    {plan.cta}
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Security ───────────────────────────────────────────────────────── */}
      <section id="security" style={{padding:"80px 48px",background:C.surface}}>
        <div style={{maxWidth:900,margin:"0 auto",textAlign:"center"}}>
          <div style={{fontSize:11,fontWeight:700,color:C.primary,
            letterSpacing:"0.1em",textTransform:"uppercase",marginBottom:8}}>
            Enterprise Security
          </div>
          <h2 style={{fontSize:36,fontWeight:800,color:C.heading,
            letterSpacing:"-0.02em",marginBottom:12}}>
            Bank-grade security for your contracts
          </h2>

          {/* AI privacy callout */}
          <div style={{padding:"16px 24px",borderRadius:12,marginBottom:40,
            background:`linear-gradient(135deg,${C.primaryLight},#F0FDFF)`,
            border:`1px solid ${C.primary}20`,
            display:"flex",alignItems:"center",gap:12,textAlign:"left"}}>
            <div style={{width:36,height:36,borderRadius:8,flexShrink:0,
              background:C.primaryLight,display:"flex",alignItems:"center",justifyContent:"center"}}>
              <Shield size={18} style={{color:C.primary}}/>
            </div>
            <div>
              <div style={{fontSize:14,fontWeight:700,color:C.heading,marginBottom:2}}>
                We never train public AI models on your private contract data.
              </div>
              <div style={{fontSize:13,color:C.muted}}>
                All LLM calls are stateless API requests. Your contracts are never used
                for model training by Groq, Gemini, or Claustor.
              </div>
            </div>
          </div>

          <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:16,marginBottom:32}}>
            {TRUST.map(t=>(
              <div key={t.label} style={{padding:"20px 16px",background:C.bg,
                borderRadius:12,border:`1px solid ${C.border}`,textAlign:"left",
                display:"flex",gap:12,alignItems:"flex-start"}}>
                <div style={{width:32,height:32,borderRadius:8,flexShrink:0,
                  background:C.primaryLight,display:"flex",alignItems:"center",
                  justifyContent:"center"}}>
                  <t.Icon size={14} style={{color:C.primary}}/>
                </div>
                <div>
                  <div style={{fontSize:13,fontWeight:700,color:C.heading,marginBottom:2}}>
                    {t.label}
                  </div>
                  <div style={{fontSize:11,color:C.muted,lineHeight:1.4}}>{t.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer CTA ─────────────────────────────────────────────────────── */}
      <section style={{padding:"80px 48px",
        background:`linear-gradient(135deg,${C.navy},#0A1F4A)`,
        textAlign:"center"}}>
        <div style={{maxWidth:600,margin:"0 auto"}}>
          <div style={{marginBottom:24,display:"flex",justifyContent:"center"}}>
            <ClauStorLogo size={56}/>
          </div>
          <h2 style={{fontSize:36,fontWeight:900,color:"white",
            letterSpacing:"-0.02em",marginBottom:12}}>
            Ready to understand your contracts?
          </h2>
          <p style={{fontSize:16,color:"rgba(255,255,255,0.7)",marginBottom:32}}>
            Join legal teams reviewing contracts 8× faster with AI.
          </p>
          <div style={{display:"flex",gap:12,justifyContent:"center"}}>
            <Link href="/register"
              style={{padding:"14px 32px",background:"white",color:C.primary,
                borderRadius:10,fontSize:16,fontWeight:800,textDecoration:"none",
                boxShadow:"0 4px 16px rgba(0,0,0,0.2)",
                display:"flex",alignItems:"center",gap:8}}>
              Start free today <ArrowRight size={16}/>
            </Link>
            <Link href="/login"
              style={{padding:"14px 28px",background:"transparent",color:"white",
                border:"2px solid rgba(255,255,255,0.3)",borderRadius:10,
                fontSize:16,fontWeight:600,textDecoration:"none"}}>
              Sign in
            </Link>
          </div>
          <p style={{fontSize:12,color:"rgba(255,255,255,0.4)",marginTop:16}}>
            Free forever · 5 contracts · No credit card
          </p>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer style={{padding:"40px 48px",background:"#060A14",
        color:"rgba(255,255,255,0.4)"}}>
        <div style={{maxWidth:1100,margin:"0 auto"}}>
          <div style={{display:"grid",gridTemplateColumns:"2fr 1fr 1fr 1fr",
            gap:32,marginBottom:32}}>
            {/* Brand */}
            <div>
              <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:12}}>
                <ClauStorLogo size={32}/>
                <span style={{fontWeight:800,fontSize:16,color:"white"}}>Claustor</span>
              </div>
              <p style={{fontSize:13,lineHeight:1.7,maxWidth:260}}>
                AI-powered contract intelligence platform built for enterprise legal teams.
              </p>
              <div style={{fontSize:12,marginTop:12,color:"rgba(255,255,255,0.25)"}}>
                Made with ❤️ in Hyderabad, India
              </div>
            </div>
            {/* Product */}
            <div>
              <div style={{fontSize:11,fontWeight:700,color:"rgba(255,255,255,0.6)",
                textTransform:"uppercase",letterSpacing:"0.08em",marginBottom:12}}>
                Product
              </div>
              {["Features","Pricing","Security","Industries","Changelog"].map(l=>(
                <div key={l} style={{marginBottom:8}}>
                  <a href="#" style={{fontSize:13,color:"rgba(255,255,255,0.4)",
                    textDecoration:"none",transition:"color 0.15s"}}
                    onMouseEnter={e=>(e.currentTarget as HTMLElement).style.color="white"}
                    onMouseLeave={e=>(e.currentTarget as HTMLElement).style.color="rgba(255,255,255,0.4)"}>
                    {l}
                  </a>
                </div>
              ))}
            </div>
            {/* Company */}
            <div>
              <div style={{fontSize:11,fontWeight:700,color:"rgba(255,255,255,0.6)",
                textTransform:"uppercase",letterSpacing:"0.08em",marginBottom:12}}>
                Company
              </div>
              {["About","Blog","Careers","Contact"].map(l=>(
                <div key={l} style={{marginBottom:8}}>
                  <a href="#" style={{fontSize:13,color:"rgba(255,255,255,0.4)",
                    textDecoration:"none"}}>{l}</a>
                </div>
              ))}
            </div>
            {/* Legal */}
            <div>
              <div style={{fontSize:11,fontWeight:700,color:"rgba(255,255,255,0.6)",
                textTransform:"uppercase",letterSpacing:"0.08em",marginBottom:12}}>
                Legal
              </div>
              {["Privacy Policy","Terms of Service","Data Processing Agreement","Cookie Policy"].map(l=>(
                <div key={l} style={{marginBottom:8}}>
                  <a href="#" style={{fontSize:13,color:"rgba(255,255,255,0.4)",
                    textDecoration:"none"}}>{l}</a>
                </div>
              ))}
            </div>
          </div>
          <div style={{borderTop:"1px solid rgba(255,255,255,0.06)",paddingTop:24,
            display:"flex",justifyContent:"space-between",alignItems:"center",
            flexWrap:"wrap",gap:12}}>
            <div style={{fontSize:12}}>
              © 2026 DKU Technologies Pvt. Ltd. All rights reserved.
            </div>
            <div style={{display:"flex",gap:16,fontSize:12}}>
              {["Privacy","Terms","Security","Contact"].map(l=>(
                <a key={l} href="#"
                  style={{color:"rgba(255,255,255,0.4)",textDecoration:"none"}}>
                  {l}
                </a>
              ))}
            </div>
          </div>
        </div>
      </footer>

      <style>{`
        * { box-sizing:border-box; margin:0; padding:0; }
        html { scroll-behavior:smooth; }
      `}</style>
    </div>
  );
}
