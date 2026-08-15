
"use client";
import Link from "next/link";
export default function SecurityPage() {
  const cards = [
    {icon:"🔐",title:"Encryption at Rest",desc:"AES-256 for all stored data. Keys managed via Google Cloud KMS."},
    {icon:"🔒",title:"Encryption in Transit",desc:"TLS 1.3 on all connections. HSTS enforced on all domains."},
    {icon:"👥",title:"Role-Based Access",desc:"Granular RBAC: Admin, Manager, Viewer roles per organisation."},
    {icon:"🏢",title:"Org Isolation",desc:"Separate Pinecone namespaces and DB filtering per organisation."},
    {icon:"📋",title:"Audit Logs",desc:"Full activity trail for all data access and admin actions. Enterprise."},
    {icon:"🌏",title:"Regional Deployment",desc:"Data in asia-south1 (Mumbai, India). Custom regions for Enterprise."},
    {icon:"🤖",title:"Private AI Option",desc:"Enterprise: isolated AI processing. Data never trains AI models."},
    {icon:"⚡",title:"Rate Limiting",desc:"Redis-backed rate limiting. Brute force protection on auth endpoints."},
  ];
  return (
    <div style={{fontFamily:"Inter,system-ui,sans-serif",background:"#FAFBFC",minHeight:"100vh"}}>
      <nav style={{background:"white",borderBottom:"1px solid #E5E7EB",padding:"0 5vw"}}>
        <div style={{maxWidth:1200,margin:"0 auto",display:"flex",alignItems:"center",height:64}}>
          <Link href="/" style={{textDecoration:"none",fontSize:18,fontWeight:800,color:"#111827"}}><span style={{color:"#06B6D4"}}>C</span>laustor</Link>
        </div>
      </nav>
      <div style={{background:"linear-gradient(135deg,#0D0F1A 0%,#1a1b35 100%)",padding:"60px 5vw"}}>
        <div style={{maxWidth:800,margin:"0 auto"}}>
          <div style={{fontSize:12,fontWeight:700,color:"#06B6D4",letterSpacing:"1.5px",marginBottom:12,textTransform:"uppercase"}}>Trust & Safety</div>
          <h1 style={{fontSize:40,fontWeight:900,color:"white",margin:"0 0 12px"}}>Security at Claustor</h1>
          <p style={{fontSize:15,color:"#64748B",margin:0}}>8-layer defence architecture built for enterprise contract intelligence.</p>
        </div>
      </div>
      <div style={{maxWidth:900,margin:"0 auto",padding:"60px 5vw"}}>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(260px,1fr))",gap:20,marginBottom:48}}>
          {cards.map(({icon,title,desc})=>(
            <div key={title} style={{background:"white",border:"1px solid #E5E7EB",borderRadius:12,padding:24}}>
              <div style={{fontSize:28,marginBottom:12}}>{icon}</div>
              <div style={{fontSize:14,fontWeight:700,color:"#111827",marginBottom:6}}>{title}</div>
              <div style={{fontSize:13,color:"#6B7280",lineHeight:1.6}}>{desc}</div>
            </div>
          ))}
        </div>
        <div style={{background:"#F0F7FF",border:"1px solid #DBEAFE",borderRadius:16,padding:32,marginBottom:32}}>
          <h2 style={{fontSize:20,fontWeight:800,color:"#111827",marginBottom:20}}>Compliance</h2>
          {[["SOC 2 Ready","Architecture designed for SOC 2 Type II audit."],["GDPR Aligned","Data processing agreements with all providers."],["ISO 27001 Aligned","Information security aligned with ISO 27001."],["PDPA (India)","Compliant with India Personal Data Protection Act."]].map(([t,d])=>(
            <div key={t} style={{display:"flex",gap:12,marginBottom:12}}>
              <span style={{color:"#22C55E",fontWeight:700,flexShrink:0}}>✓</span>
              <div><div style={{fontSize:14,fontWeight:700,color:"#111827"}}>{t}</div><div style={{fontSize:13,color:"#6B7280"}}>{d}</div></div>
            </div>
          ))}
        </div>
        <div style={{background:"#111827",borderRadius:16,padding:32,textAlign:"center"}}>
          <h2 style={{fontSize:20,fontWeight:800,color:"white",marginBottom:12}}>Report a Security Issue</h2>
          <p style={{fontSize:14,color:"#9CA3AF",marginBottom:20}}>We respond within 24 hours.</p>
          <a href="mailto:security@claustor.com" style={{display:"inline-flex",alignItems:"center",gap:8,background:"#0066FF",color:"white",fontWeight:700,padding:"12px 28px",borderRadius:10,textDecoration:"none",fontSize:14}}>security@claustor.com →</a>
        </div>
      </div>
      <div style={{background:"#111827",padding:"24px 5vw",textAlign:"center"}}>
        <p style={{fontSize:12,color:"#6B7280",margin:0}}>© 2026 DKU Technologies Pvt. Ltd. · <Link href="/privacy" style={{color:"#0066FF",textDecoration:"none"}}>Privacy</Link> · <Link href="/terms" style={{color:"#0066FF",textDecoration:"none"}}>Terms</Link></p>
      </div>
    </div>
  );
}
