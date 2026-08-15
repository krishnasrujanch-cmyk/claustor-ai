
"use client";
import { useState } from "react";
import Link from "next/link";
export default function ContactPage() {
  const [form, setForm] = useState({name:"",email:"",company:"",subject:"",message:""});
  const [sent, setSent] = useState(false);
  const handleSubmit = async () => {
    try {
      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${API}/api/v1/billing/enterprise/contact`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({business_name:form.company||"Not provided",contact_name:form.name,business_email:form.email,company_size:"",message:`[${form.subject}] ${form.message}`,industry:form.subject}),
      });
    } catch {}
    setSent(true);
  };
  const contacts = [
    {icon:"💼",title:"Sales & Pricing",email:"sales@claustor.com",desc:"Enterprise plans, demos, custom pricing"},
    {icon:"🛠️",title:"Technical Support",email:"support@claustor.com",desc:"Platform issues, API, integrations"},
    {icon:"🔒",title:"Privacy & Data",email:"privacy@claustor.com",desc:"Data requests, GDPR, deletion"},
    {icon:"⚠️",title:"Security",email:"security@claustor.com",desc:"Vulnerability reports"},
    {icon:"📧",title:"General",email:"hello@claustor.com",desc:"Everything else"},
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
          <div style={{fontSize:12,fontWeight:700,color:"#06B6D4",letterSpacing:"1.5px",marginBottom:12,textTransform:"uppercase"}}>Get in Touch</div>
          <h1 style={{fontSize:40,fontWeight:900,color:"white",margin:"0 0 12px"}}>Contact Us</h1>
          <p style={{fontSize:15,color:"#64748B",margin:0}}>We respond within 4 business hours.</p>
        </div>
      </div>
      <div style={{maxWidth:900,margin:"0 auto",padding:"60px 5vw"}}>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:48}}>
          <div>
            <h2 style={{fontSize:20,fontWeight:800,color:"#111827",marginBottom:24}}>Send a Message</h2>
            {sent ? (
              <div style={{textAlign:"center",padding:"40px 0"}}>
                <div style={{fontSize:48,marginBottom:16}}>✅</div>
                <div style={{fontSize:20,fontWeight:700,color:"#111827",marginBottom:8}}>Message Sent!</div>
                <div style={{fontSize:14,color:"#6B7280"}}>We will get back within 4 business hours.</div>
              </div>
            ) : (
              <>
                {[{key:"name",label:"Full Name *",ph:"Jane Smith"},{key:"email",label:"Email *",ph:"jane@company.com"},{key:"company",label:"Company",ph:"Acme Corp"}].map(({key,label,ph})=>(
                  <div key={key} style={{marginBottom:14}}>
                    <label style={{fontSize:12,fontWeight:600,color:"#374151",display:"block",marginBottom:4}}>{label}</label>
                    <input placeholder={ph} value={(form as any)[key]} onChange={e=>setForm(f=>({...f,[key]:e.target.value}))}
                      style={{width:"100%",padding:"10px 12px",border:"1px solid #E5E7EB",borderRadius:8,fontSize:13,boxSizing:"border-box"}}/>
                  </div>
                ))}
                <div style={{marginBottom:14}}>
                  <label style={{fontSize:12,fontWeight:600,color:"#374151",display:"block",marginBottom:4}}>Subject *</label>
                  <select value={form.subject} onChange={e=>setForm(f=>({...f,subject:e.target.value}))}
                    style={{width:"100%",padding:"10px 12px",border:"1px solid #E5E7EB",borderRadius:8,fontSize:13,background:"white"}}>
                    <option value="">Select...</option>
                    <option>Sales and Pricing</option>
                    <option>Enterprise Plan</option>
                    <option>Technical Support</option>
                    <option>Partnership</option>
                    <option>Privacy and Data</option>
                    <option>Other</option>
                  </select>
                </div>
                <div style={{marginBottom:20}}>
                  <label style={{fontSize:12,fontWeight:600,color:"#374151",display:"block",marginBottom:4}}>Message *</label>
                  <textarea value={form.message} onChange={e=>setForm(f=>({...f,message:e.target.value}))} placeholder="How can we help?" rows={5}
                    style={{width:"100%",padding:"10px 12px",border:"1px solid #E5E7EB",borderRadius:8,fontSize:13,boxSizing:"border-box",resize:"vertical"}}/>
                </div>
                <button onClick={handleSubmit} disabled={!form.name||!form.email||!form.subject||!form.message}
                  style={{width:"100%",padding:"13px",background:"#0066FF",color:"white",border:"none",borderRadius:10,fontSize:15,fontWeight:700,cursor:"pointer",opacity:(!form.name||!form.email||!form.subject||!form.message)?0.5:1}}>
                  Send Message →
                </button>
                <div style={{fontSize:11,color:"#9CA3AF",textAlign:"center",marginTop:8}}>Goes to hello@claustor.com · Response within 4 hours</div>
              </>
            )}
          </div>
          <div>
            <h2 style={{fontSize:20,fontWeight:800,color:"#111827",marginBottom:24}}>Other Ways to Reach Us</h2>
            {contacts.map(({icon,title,email,desc})=>(
              <div key={title} style={{display:"flex",gap:14,marginBottom:16,padding:"14px 16px",background:"white",border:"1px solid #E5E7EB",borderRadius:12}}>
                <div style={{fontSize:22,flexShrink:0}}>{icon}</div>
                <div>
                  <div style={{fontSize:13,fontWeight:700,color:"#111827",marginBottom:2}}>{title}</div>
                  <a href={`mailto:${email}`} style={{fontSize:13,color:"#0066FF",textDecoration:"none",fontWeight:600}}>{email}</a>
                  <div style={{fontSize:12,color:"#9CA3AF",marginTop:2}}>{desc}</div>
                </div>
              </div>
            ))}
            <div style={{background:"#F0F7FF",border:"1px solid #DBEAFE",borderRadius:12,padding:16,marginTop:8}}>
              <div style={{fontSize:13,fontWeight:700,color:"#0066FF",marginBottom:6}}>📍 OFFICE</div>
              <div style={{fontSize:13,color:"#374151",lineHeight:1.7}}>DKU Technologies Pvt. Ltd.<br/>Hyderabad, Telangana, India</div>
            </div>
          </div>
        </div>
      </div>
      <div style={{background:"#111827",padding:"24px 5vw",textAlign:"center"}}>
        <p style={{fontSize:12,color:"#6B7280",margin:0}}>© 2026 DKU Technologies Pvt. Ltd. · <Link href="/privacy" style={{color:"#0066FF",textDecoration:"none"}}>Privacy</Link> · <Link href="/terms" style={{color:"#0066FF",textDecoration:"none"}}>Terms</Link> · <Link href="/security" style={{color:"#0066FF",textDecoration:"none"}}>Security</Link></p>
      </div>
    </div>
  );
}
