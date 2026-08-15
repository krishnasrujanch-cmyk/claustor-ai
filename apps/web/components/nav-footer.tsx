"use client";
import Link from "next/link";

export function Nav() {
  return (
    <nav style={{background:"white",borderBottom:"1px solid #E5E7EB",padding:"0 5vw",position:"sticky",top:0,zIndex:100}}>
      <div style={{maxWidth:1200,margin:"0 auto",display:"flex",alignItems:"center",justifyContent:"space-between",height:64}}>
        <Link href="/" style={{textDecoration:"none",display:"flex",alignItems:"center",gap:8}}>
          <svg width="32" height="32" viewBox="0 0 36 36" fill="none">
            <path d="M28 8C24.5 5.5 20 4 15 4C8.4 4 3 9.4 3 18s5.4 14 12 14c5 0 9.5-1.5 13-4"
              stroke="url(#ng)" strokeWidth="4" strokeLinecap="round" fill="none"/>
            <circle cx="28" cy="8" r="2.5" fill="#06B6D4"/>
            <circle cx="28" cy="28" r="2.5" fill="#06B6D4"/>
            <rect x="11" y="11" width="11" height="14" rx="2" fill="#1E293B" stroke="#334155" strokeWidth="1"/>
            <line x1="13" y1="15" x2="20" y2="15" stroke="#94A3B8" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="13" y1="18" x2="20" y2="18" stroke="#94A3B8" strokeWidth="1.5" strokeLinecap="round"/>
            <line x1="13" y1="21" x2="18" y2="21" stroke="#06B6D4" strokeWidth="1.5" strokeLinecap="round"/>
            <defs>
              <linearGradient id="ng" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#8B5CF6"/>
                <stop offset="100%" stopColor="#06B6D4"/>
              </linearGradient>
            </defs>
          </svg>
          <span style={{fontSize:18,fontWeight:800,color:"#111827"}}>
            <span style={{color:"#06B6D4"}}>C</span>laustor
          </span>
        </Link>
        <div style={{display:"flex",gap:24,alignItems:"center"}}>
          {[["Features","/#features"],["Pricing","/#pricing"],["Security","/security"],["Contact","/contact"]].map(([label,href])=>(
            <Link key={label} href={href} style={{fontSize:14,fontWeight:500,color:"#374151",textDecoration:"none"}}>{label}</Link>
          ))}
          <Link href="/login" style={{fontSize:14,fontWeight:500,color:"#374151",textDecoration:"none"}}>Sign in</Link>
          <Link href="/register" style={{display:"inline-block",background:"#0066FF",color:"white",fontWeight:700,fontSize:14,padding:"8px 20px",borderRadius:8,textDecoration:"none"}}>Start Free</Link>
        </div>
      </div>
    </nav>
  );
}

export function Footer() {
  return (
    <footer style={{background:"#111827",padding:"32px 5vw"}}>
      <div style={{maxWidth:1200,margin:"0 auto",display:"flex",justifyContent:"space-between",alignItems:"center",flexWrap:"wrap",gap:16}}>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <span style={{fontSize:16,fontWeight:800,color:"white"}}><span style={{color:"#06B6D4"}}>C</span>laustor AI</span>
          <span style={{fontSize:12,color:"#4B5563",marginLeft:8}}>© 2026 DKU Technologies Pvt. Ltd.</span>
        </div>
        <div style={{display:"flex",gap:20,flexWrap:"wrap"}}>
          {[["Privacy","/privacy"],["Terms","/terms"],["Security","/security"],["Contact","/contact"]].map(([label,href])=>(
            <Link key={label} href={href} style={{fontSize:13,color:"#6B7280",textDecoration:"none"}}>{label}</Link>
          ))}
        </div>
        <div style={{fontSize:12,color:"#374151"}}>Powered by Anthropic · OpenAI · Pinecone</div>
      </div>
    </footer>
  );
}

export function PageHero({badge,title,subtitle}:{badge:string,title:string,subtitle:string}) {
  return (
    <div style={{background:"linear-gradient(135deg,#0D0F1A 0%,#1a1b35 100%)",padding:"60px 5vw"}}>
      <div style={{maxWidth:800,margin:"0 auto"}}>
        <div style={{fontSize:12,fontWeight:700,color:"#06B6D4",letterSpacing:"1.5px",marginBottom:12,textTransform:"uppercase"}}>{badge}</div>
        <h1 style={{fontSize:40,fontWeight:900,color:"white",margin:"0 0 12px",letterSpacing:"-1px"}}>{title}</h1>
        <p style={{fontSize:15,color:"#64748B",margin:0}}>{subtitle}</p>
      </div>
    </div>
  );
}

export function Section({num,title,children}:{num:string,title:string,children:React.ReactNode}) {
  return (
    <div style={{marginBottom:40,paddingBottom:40,borderBottom:"1px solid #E5E7EB"}}>
      <div style={{display:"flex",gap:16,alignItems:"flex-start"}}>
        <div style={{width:32,height:32,borderRadius:"50%",background:"#0066FF",display:"flex",alignItems:"center",justifyContent:"center",fontSize:13,fontWeight:700,color:"white",flexShrink:0,marginTop:2}}>{num}</div>
        <div style={{flex:1}}>
          <h2 style={{fontSize:20,fontWeight:800,color:"#111827",margin:"0 0 16px"}}>{title}</h2>
          <div>{children}</div>
        </div>
      </div>
    </div>
  );
}

export function Item({children}:{children:React.ReactNode}) {
  return (
    <div style={{display:"flex",gap:8,marginBottom:10,alignItems:"flex-start"}}>
      <span style={{color:"#0066FF",fontWeight:700,flexShrink:0,marginTop:1}}>·</span>
      <div style={{fontSize:14,color:"#374151",lineHeight:1.7}}>{children}</div>
    </div>
  );
}
