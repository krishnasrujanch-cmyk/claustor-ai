"use client";
import { Nav, Footer, PageHero, Section, Item } from "@/components/nav-footer";

export default function PrivacyPage() {
  return (
    <div style={{fontFamily:"Inter,system-ui,sans-serif",background:"#FAFBFC",minHeight:"100vh"}}>
      <Nav/>
      <PageHero badge="Legal" title="Privacy Policy" subtitle="Last updated: August 2026 — DKU Technologies Pvt. Ltd."/>
      <div style={{maxWidth:800,margin:"0 auto",padding:"60px 5vw"}}>

        <div style={{background:"#EFF6FF",border:"1px solid #DBEAFE",borderRadius:12,padding:"20px 24px",marginBottom:48}}>
          <div style={{fontSize:13,fontWeight:700,color:"#0066FF",marginBottom:10}}>SUMMARY — KEY POINTS</div>
          {["Your contracts are encrypted and private — we do not sell your data.",
            "AI providers (Anthropic, OpenAI) process contract content for analysis only.",
            "AI providers do NOT use your contracts to train their models.",
            "You can request deletion of your data at any time.",
            "Enterprise customers can request private AI deployment."].map(t=>(
            <div key={t} style={{display:"flex",gap:8,marginBottom:6,fontSize:13,color:"#374151"}}>
              <span style={{color:"#22C55E",fontWeight:700}}>✓</span>{t}
            </div>
          ))}
        </div>

        <Section num="1" title="Information We Collect">
          <Item>Account information: name, email address, organisation name, and role.</Item>
          <Item>Contract documents you upload for analysis.</Item>
          <Item>Usage data: queries, feature usage, and session information.</Item>
          <Item>Payment information: processed securely by Razorpay — we never store card details.</Item>
        </Section>

        <Section num="2" title="How We Use Your Information">
          <Item>To provide contract analysis, risk scoring, and AI Copilot services.</Item>
          <Item>To send transactional notifications such as analysis complete and renewal reminders.</Item>
          <Item>To process payments and manage your subscription.</Item>
          <Item>To improve platform reliability and performance.</Item>
        </Section>

        <Section num="3" title="AI Processing — Important">
          <Item>When you upload a contract, its content is sent to AI providers (Anthropic Claude, OpenAI GPT) for analysis.</Item>
          <Item>By creating an account and uploading contracts, you consent to this AI processing.</Item>
          <Item>Anthropic and OpenAI process data under strict data processing agreements and do not use your content to train their models.</Item>
          <Item>Contract content is transmitted over TLS 1.3 and is not stored by AI providers beyond the immediate processing request.</Item>
          <Item>Enterprise customers may request a private AI deployment option where data does not leave your infrastructure.</Item>
        </Section>

        <Section num="4" title="Data Storage and Security">
          <Item>Documents are stored encrypted at rest (AES-256) in Google Cloud Storage, asia-south1 region (Mumbai, India).</Item>
          <Item>Database records are stored in encrypted PostgreSQL.</Item>
          <Item>Vector embeddings are stored in Pinecone with per-organisation namespace isolation.</Item>
          <Item>All data is transmitted over TLS 1.3 and access is controlled via role-based permissions.</Item>
          <Item>All data access actions are logged in our audit system.</Item>
        </Section>

        <Section num="5" title="Data Sharing">
          <Item>We do not sell your data to third parties.</Item>
          <Item>We share data only with: Anthropic (AI analysis), OpenAI (AI analysis), Google Cloud (storage), Neon (database), Pinecone (vector search), Resend (email), Razorpay (payments).</Item>
          <Item>All service providers are bound by data processing agreements.</Item>
          <Item>We may disclose data if required by law or to protect legal rights.</Item>
        </Section>

        <Section num="6" title="Data Retention">
          <Item>Contract data is retained for the duration of your active subscription.</Item>
          <Item>After cancellation, data is retained for 30 days then permanently deleted.</Item>
          <Item>You may request immediate deletion by contacting privacy@claustor.com.</Item>
          <Item>Enterprise audit logs are retained for 12 months.</Item>
        </Section>

        <Section num="7" title="Your Rights">
          <Item>Access: request a copy of all personal data we hold about you.</Item>
          <Item>Correction: request correction of inaccurate personal data.</Item>
          <Item>Deletion: request permanent deletion of your data.</Item>
          <Item>Export: download all your contracts and data.</Item>
          <Item>Contact privacy@claustor.com — we respond within 30 days.</Item>
        </Section>

        <Section num="8" title="Contact">
          <Item>Privacy Officer: privacy@claustor.com</Item>
          <Item>General: hello@claustor.com</Item>
          <Item>DKU Technologies Pvt. Ltd., Hyderabad, Telangana, India</Item>
        </Section>

        <div style={{textAlign:"center",padding:"32px 0 0"}}>
          <a href="mailto:privacy@claustor.com" style={{display:"inline-flex",alignItems:"center",gap:8,background:"#0066FF",color:"white",fontWeight:700,padding:"12px 28px",borderRadius:10,textDecoration:"none",fontSize:14}}>
            Contact Privacy Officer →
          </a>
        </div>
      </div>
      <Footer/>
    </div>
  );
}
