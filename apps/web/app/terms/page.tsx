
"use client";
import Link from "next/link";
export default function TermsPage() {
  const sections = [
    { num:"1", title:"Acceptance of Terms", items:["By using Claustor AI you agree to these terms.","If you disagree, please do not use the service."] },
    { num:"2", title:"Description of Service", items:["Claustor AI is an enterprise contract intelligence platform.","We provide clause extraction, risk scoring, obligation tracking and AI Q&A.","Available on Free, Starter, Professional and Enterprise plans."] },
    { num:"3", title:"User Responsibilities", items:["Maintain confidentiality of your account credentials.","Only upload contracts you have rights to process.","Do not reverse engineer or abuse the platform."] },
    { num:"4", title:"AI Processing Consent", items:["Uploading contracts constitutes consent to AI processing by Anthropic and OpenAI.","AI providers do not train models on your data.","Enterprise customers may request private AI deployment."] },
    { num:"5", title:"Payment & Billing", items:["Subscriptions billed monthly in advance in INR.","Refunds available within 7 days for first-time subscribers.","Payments processed securely by Razorpay."] },
    { num:"6", title:"Intellectual Property", items:["Claustor AI is the intellectual property of DKU Technologies Pvt. Ltd.","Your contracts remain your property — we claim no ownership.","AI analyses are tools to assist decision-making, not legal advice."] },
    { num:"7", title:"Limitation of Liability", items:["Claustor AI is not a substitute for professional legal advice.","Maximum liability limited to 3 months of paid subscription fees."] },
    { num:"8", title:"Termination", items:["Cancel anytime from the billing dashboard.","Data retained 30 days after cancellation then permanently deleted."] },
    { num:"9", title:"Governing Law", items:["Governed by the laws of India.","Disputes subject to courts in Hyderabad, Telangana, India."] },
    { num:"10", title:"Contact", items:["Legal: legal@claustor.com","General: hello@claustor.com","DKU Technologies Pvt. Ltd., Hyderabad, India"] },
  ];
  return (
    <div style={{fontFamily:"Inter,system-ui,sans-serif",background:"#FAFBFC",minHeight:"100vh"}}>
      <nav style={{background:"white",borderBottom:"1px solid #E5E7EB",padding:"0 5vw"}}>
        <div style={{maxWidth:1200,margin:"0 auto",display:"flex",alignItems:"center",height:64}}>
          <Link href="/" style={{textDecoration:"none",fontSize:18,fontWeight:800,color:"#111827"}}>
            <span style={{color:"#06B6D4"}}>C</span>laustor
          </Link>
        </div>
      </nav>
      <div style={{background:"linear-gradient(135deg,#0D0F1A 0%,#1a1b35 100%)",padding:"60px 5vw"}}>
        <div style={{maxWidth:800,margin:"0 auto"}}>
          <div style={{fontSize:12,fontWeight:700,color:"#06B6D4",letterSpacing:"1.5px",marginBottom:12,textTransform:"uppercase"}}>Legal</div>
          <h1 style={{fontSize:40,fontWeight:900,color:"white",margin:"0 0 12px"}}>Terms of Service</h1>
          <p style={{fontSize:15,color:"#64748B",margin:0}}>Last updated: August 2026 · DKU Technologies Pvt. Ltd.</p>
        </div>
      </div>
      <div style={{maxWidth:800,margin:"0 auto",padding:"60px 5vw"}}>
        {sections.map(({num,title,items})=>(
          <div key={num} style={{marginBottom:40,paddingBottom:40,borderBottom:"1px solid #E5E7EB"}}>
            <div style={{display:"flex",gap:16,alignItems:"flex-start"}}>
              <div style={{width:32,height:32,borderRadius:"50%",background:"#0066FF",display:"flex",alignItems:"center",justifyContent:"center",fontSize:13,fontWeight:700,color:"white",flexShrink:0,marginTop:2}}>{num}</div>
              <div style={{flex:1}}>
                <h2 style={{fontSize:20,fontWeight:800,color:"#111827",margin:"0 0 16px"}}>{title}</h2>
                {items.map((line,i)=>(
                  <div key={i} style={{display:"flex",gap:8,marginBottom:10}}>
                    <span style={{color:"#0066FF",fontWeight:700,flexShrink:0}}>·</span>
                    <p style={{fontSize:14,color:"#374151",lineHeight:1.7,margin:0}}>{line}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
        <div style={{textAlign:"center",padding:"20px 0"}}>
          <a href="mailto:legal@claustor.com" style={{display:"inline-flex",alignItems:"center",gap:8,background:"#0066FF",color:"white",fontWeight:700,padding:"12px 28px",borderRadius:10,textDecoration:"none",fontSize:14}}>
            Contact Legal Team →
          </a>
        </div>
      </div>
      <div style={{background:"#111827",padding:"24px 5vw",textAlign:"center"}}>
        <p style={{fontSize:12,color:"#6B7280",margin:0}}>© 2026 DKU Technologies Pvt. Ltd. · <Link href="/privacy" style={{color:"#0066FF",textDecoration:"none"}}>Privacy</Link> · <Link href="/terms" style={{color:"#0066FF",textDecoration:"none"}}>Terms</Link> · <a href="mailto:hello@claustor.com" style={{color:"#0066FF",textDecoration:"none"}}>Contact</a></p>
      </div>
    </div>
  );
}
