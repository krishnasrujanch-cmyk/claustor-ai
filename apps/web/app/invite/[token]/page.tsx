"use client";
export const dynamic = "force-dynamic";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { C } from "@/lib/design-tokens";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export default function InvitePage() {
  const { token } = useParams();
  const router    = useRouter();

  const [step, setStep]         = useState<"loading"|"form"|"done"|"error">("loading");
  const [inviteData, setInviteData] = useState<any>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm]   = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg]           = useState("");

  // Validate token on load
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/v1/auth/validate-invite/${token}`)
      .then(r => r.json())
      .then(d => {
        if (d.valid) {
          setInviteData(d);
          setStep("form");
        } else {
          setMsg(d.detail || "Invalid or expired invite link");
          setStep("error");
        }
      })
      .catch(() => { setMsg("Could not validate invite link"); setStep("error"); });
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setMsg("Passwords do not match"); return; }
    if (password.length < 8)  { setMsg("Password must be at least 8 characters"); return; }

    setSubmitting(true); setMsg("");
    try {
      const r = await fetch(`${API}/api/v1/auth/accept-invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Failed to set password");
      setStep("done");
      // Auto-redirect to login after 2s
      setTimeout(() => router.push("/login"), 2000);
    } catch(e:any) { setMsg(e.message); }
    finally { setSubmitting(false); }
  };

  return (
    <div style={{minHeight:"100vh", background:"#F9FAFB",
      display:"flex", alignItems:"center", justifyContent:"center"}}>
      <div style={{background:C.surface, border:`1px solid ${C.border}`,
        borderRadius:16, padding:40, width:400, boxShadow:"0 4px 24px rgba(0,0,0,0.08)"}}>

        {/* Logo */}
        <div style={{textAlign:"center", marginBottom:32}}>
          <div style={{fontSize:28, marginBottom:8}}>🔗</div>
          <h1 style={{fontSize:24, fontWeight:800, color:C.primary, marginBottom:4}}>
            Claustor AI
          </h1>
          <p style={{fontSize:14, color:C.muted}}>You've been invited to join</p>
        </div>

        {step === "loading" && (
          <div style={{textAlign:"center", color:C.muted, padding:20}}>
            Validating invite link...
          </div>
        )}

        {step === "error" && (
          <div style={{textAlign:"center"}}>
            <div style={{fontSize:40, marginBottom:16}}>❌</div>
            <p style={{color:C.error, fontSize:14, marginBottom:24}}>{msg}</p>
            <button onClick={() => router.push("/login")}
              style={{padding:"10px 24px", background:C.primary, color:"white",
                border:"none", borderRadius:8, fontSize:14, fontWeight:600,
                cursor:"pointer"}}>
              Go to Login
            </button>
          </div>
        )}

        {step === "form" && inviteData && (
          <>
            <div style={{background:"#F0FDF4", borderRadius:8, padding:16,
              marginBottom:24, fontSize:14}}>
              <div style={{fontWeight:600, color:"#16A34A", marginBottom:4}}>
                ✅ Invite valid
              </div>
              <div style={{color:C.body}}>
                <strong>{inviteData.email}</strong>
              </div>
              <div style={{color:C.muted, fontSize:12, marginTop:4}}>
                Role: {inviteData.role?.replace(/_/g," ")}
              </div>
            </div>

            {msg && (
              <div style={{padding:"10px 12px", background:"#FEF2F2",
                borderRadius:8, color:C.error, fontSize:13, marginBottom:16}}>
                {msg}
              </div>
            )}

            <form onSubmit={handleSubmit} style={{display:"flex", flexDirection:"column", gap:16}}>
              <div>
                <label style={{display:"block", fontSize:13, fontWeight:600,
                  color:C.body, marginBottom:6}}>Set Password</label>
                <input type="password" value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters" required minLength={8}
                  style={{width:"100%", padding:"10px 14px",
                    border:`1.5px solid ${C.border}`, borderRadius:8,
                    fontSize:14, color:C.body, boxSizing:"border-box"}} />
              </div>
              <div>
                <label style={{display:"block", fontSize:13, fontWeight:600,
                  color:C.body, marginBottom:6}}>Confirm Password</label>
                <input type="password" value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  placeholder="Repeat password" required
                  style={{width:"100%", padding:"10px 14px",
                    border:`1.5px solid ${C.border}`, borderRadius:8,
                    fontSize:14, color:C.body, boxSizing:"border-box"}} />
              </div>
              <button type="submit" disabled={submitting}
                style={{padding:"12px", background:C.primary, color:"white",
                  border:"none", borderRadius:8, fontSize:15, fontWeight:700,
                  cursor:submitting?"not-allowed":"pointer", marginTop:4}}>
                {submitting ? "Setting up account..." : "Accept Invitation →"}
              </button>
            </form>
          </>
        )}

        {step === "done" && (
          <div style={{textAlign:"center"}}>
            <div style={{fontSize:48, marginBottom:16}}>🎉</div>
            <h2 style={{fontSize:20, fontWeight:700, color:C.heading, marginBottom:8}}>
              Account created!
            </h2>
            <p style={{color:C.muted, fontSize:14}}>
              Redirecting to login...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
