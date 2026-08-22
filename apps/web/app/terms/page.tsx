"use client";
export const dynamic = "force-dynamic";
import Link from "next/link";

export default function TermsPage() {
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
          <p style={{fontSize:15,color:"#64748B",margin:0}}>Last updated: August 2026 — DKU Technologies Pvt. Ltd.</p>
        </div>
      </div>

      <div style={{maxWidth:800,margin:"0 auto",padding:"60px 5vw"}}>

        <Section num="1" title="Acceptance of Terms">
          <Item>These Terms of Service govern your access to and use of Claustor AI, operated by DKU Technologies Pvt. Ltd.</Item>
          <Item>By creating an account or using any part of the service, you agree to be bound by these terms.</Item>
          <Item>If you do not agree to these terms, you must not access or use Claustor AI.</Item>
          <Item>These terms apply to all users including organisation administrators, managers, and viewers.</Item>
        </Section>

        <Section num="2" title="Description of Service">
          <Item>Claustor AI is an enterprise contract intelligence platform powered by artificial intelligence.</Item>
          <Item>The platform provides: contract upload and storage, AI-powered clause extraction (25+ types), risk scoring and playbook matching, obligation and renewal tracking, natural language Q&A via AI Copilot, and party identifier extraction across 8 countries.</Item>
          <Item>The service is available on Free, Starter (₹7,999/mo), Professional (₹29,999/mo), and Enterprise (custom) plans.</Item>
          <Item>Features available depend on your subscription plan. Plan details are available at claustor.com/pricing.</Item>
        </Section>

        <Section num="3" title="User Accounts and Responsibilities">
          <Item>You must provide accurate information when creating your account and keep it updated.</Item>
          <Item>You are responsible for maintaining the confidentiality of your login credentials.</Item>
          <Item>You must not share your account with others outside your organisation.</Item>
          <Item>You must only upload contracts and documents for which you have appropriate authorisation.</Item>
          <Item>You must not attempt to reverse engineer, decompile, or circumvent any part of the platform.</Item>
          <Item>You are responsible for ensuring your use of Claustor AI complies with applicable laws in your jurisdiction.</Item>
          <Item>You must not use the platform to process personal data in violation of applicable data protection laws.</Item>
        </Section>

        <Section num="4" title="AI Processing and Data Consent">
          <Item>By uploading contracts to Claustor AI, you consent to the processing of that content by AI providers including Anthropic (Claude) and OpenAI (GPT models).</Item>
          <Item>AI providers process your contract content solely to provide the analysis services you have requested.</Item>
          <Item>Neither Anthropic nor OpenAI use your contract content to train their AI models. This is governed by their respective data processing agreements.</Item>
          <Item>Contract content is transmitted over encrypted connections (TLS 1.3) and is not retained by AI providers beyond the immediate processing request.</Item>
          <Item>Enterprise customers may request a private AI deployment option where data processing occurs within a dedicated environment.</Item>
          <Item>AI-generated analyses, risk scores, and Q&A responses are provided as tools to assist your team. They do not constitute legal advice and should not be relied upon as a substitute for professional legal counsel.</Item>
        </Section>

        <Section num="5" title="Payment and Billing">
          <Item>Paid subscriptions are billed monthly in advance in Indian Rupees (INR) inclusive of applicable GST.</Item>
          <Item>Payments are processed securely by Razorpay. We do not store your card or bank details.</Item>
          <Item>Subscriptions automatically renew each month unless cancelled before the renewal date.</Item>
          <Item>Refunds are available within 7 days of the initial payment for new subscribers. No refunds are available for subsequent billing cycles.</Item>
          <Item>If payment fails, we will retry within 3 days. If unsuccessful, your account may be downgraded to the Free plan.</Item>
          <Item>Extra user seats are billed at the per-user rate for your plan (Starter: ₹800/user, Professional: ₹1,500/user).</Item>
          <Item>Enterprise pricing is custom — contact sales@claustor.com for details.</Item>
        </Section>

        <Section num="6" title="Intellectual Property">
          <Item>Claustor AI, its software, features, algorithms, and branding are the intellectual property of DKU Technologies Pvt. Ltd. All rights reserved.</Item>
          <Item>Your contract documents remain your property. We claim no ownership over any content you upload.</Item>
          <Item>AI-generated analyses and outputs are provided for your use. We do not claim intellectual property rights over analysis outputs.</Item>
          <Item>You may not copy, reproduce, or redistribute any part of Claustor AI without prior written permission.</Item>
        </Section>

        <Section num="7" title="Disclaimers and Limitation of Liability">
          <Item>Claustor AI is a technology tool designed to assist legal and commercial teams. It is not a law firm and does not provide legal advice.</Item>
          <Item>AI analyses may contain errors or omissions. Always verify important findings with qualified legal professionals before making decisions.</Item>
          <Item>The service is provided "as is" without warranties of any kind, express or implied.</Item>
          <Item>We are not liable for any indirect, incidental, or consequential damages arising from your use of the service.</Item>
          <Item>Our maximum aggregate liability for any claim is limited to the total amount you paid in the 3 months preceding the claim.</Item>
        </Section>

        <Section num="8" title="Termination">
          <Item>You may cancel your subscription at any time from the Billing section of your dashboard.</Item>
          <Item>Cancellation takes effect at the end of the current billing period. You retain access until then.</Item>
          <Item>We may suspend or terminate accounts that violate these terms, with or without prior notice depending on severity.</Item>
          <Item>Upon termination, your data is retained for 30 days and then permanently and irreversibly deleted.</Item>
          <Item>You may request immediate deletion by emailing privacy@claustor.com.</Item>
        </Section>

        <Section num="9" title="Changes to Terms">
          <Item>We may update these terms from time to time to reflect changes in our services or applicable laws.</Item>
          <Item>We will notify you by email at least 30 days before any material changes take effect.</Item>
          <Item>Your continued use of Claustor AI after the effective date constitutes acceptance of the updated terms.</Item>
          <Item>If you do not agree to the updated terms, you must cancel your subscription before the effective date.</Item>
        </Section>

        <Section num="10" title="Governing Law and Disputes">
          <Item>These Terms of Service are governed by and construed in accordance with the laws of India.</Item>
          <Item>Any disputes arising from these terms or your use of Claustor AI shall be subject to the exclusive jurisdiction of the competent courts in Hyderabad, Telangana, India.</Item>
          <Item>We encourage resolution of disputes through direct communication before initiating legal proceedings. Contact legal@claustor.com.</Item>
        </Section>

        <Section num="11" title="Contact Information">
          <Item>Legal enquiries: legal@claustor.com</Item>
          <Item>General enquiries: hello@claustor.com</Item>
          <Item>Privacy and data: privacy@claustor.com</Item>
          <Item>DKU Technologies Pvt. Ltd., Hyderabad, Telangana, India — 500 001</Item>
        </Section>

        <div style={{textAlign:"center",padding:"32px 0 0"}}>
          <a href="mailto:legal@claustor.com" style={{display:"inline-flex",alignItems:"center",gap:8,background:"#0066FF",color:"white",fontWeight:700,padding:"12px 28px",borderRadius:10,textDecoration:"none",fontSize:14}}>
            Contact Legal Team →
          </a>
        </div>
      </div>

      <div style={{background:"#111827",padding:"24px 5vw",textAlign:"center"}}>
        <p style={{fontSize:12,color:"#6B7280",margin:0}}>
          © 2026 DKU Technologies Pvt. Ltd. ·{" "}
          <Link href="/privacy" style={{color:"#0066FF",textDecoration:"none"}}>Privacy</Link>{" "}·{" "}
          <Link href="/terms" style={{color:"#0066FF",textDecoration:"none"}}>Terms</Link>{" "}·{" "}
          <Link href="/security" style={{color:"#0066FF",textDecoration:"none"}}>Security</Link>{" "}·{" "}
          <Link href="/contact" style={{color:"#0066FF",textDecoration:"none"}}>Contact</Link>
        </p>
      </div>
    </div>
  );
}

function Section({ num, title, children }: { num: string; title: string; children: React.ReactNode }) {
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

function Item({ children }: { children: React.ReactNode }) {
  return (
    <div style={{display:"flex",gap:8,marginBottom:10,alignItems:"flex-start"}}>
      <span style={{color:"#0066FF",fontWeight:700,flexShrink:0,marginTop:1}}>·</span>
      <div style={{fontSize:14,color:"#374151",lineHeight:1.7}}>{children}</div>
    </div>
  );
}
