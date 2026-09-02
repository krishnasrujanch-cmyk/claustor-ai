"use client";
import { API_URL as API } from "@/lib/config";

export const dynamic = "force-dynamic";
import { ClauStorLoader } from "@/components/shared/ClauStorLoader";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect, useRef, Suspense } from "react";
import { useAuthStore } from "@/store/auth";
import { Eye, EyeOff, CheckCircle, Zap, Shield, Clock } from "lucide-react";

const C = {
  primary:"#0066FF", primaryHover:"#0052CC", primaryLight:"#E6F0FF",
  accent:"#00A3FF", navy:"#0A1128",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", error:"#EF4444", errorLight:"#FEF2F2",
  surface:"#FFFFFF", bg:"#FAFBFC", success:"#22C55E",
};

// ── Animated counter ──────────────────────────────────────────────────────────
function Counter({ target, suffix="" }: { target: number; suffix?: string }) {
  const [val, setVal] = useState(0);
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const step = target / 60;
    let current = 0;
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      setVal(Math.floor(current));
      if (current >= target) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [target]);
  return <>{val.toLocaleString()}{suffix}</>;
}

// ── Testimonials ──────────────────────────────────────────────────────────────
const TESTIMONIALS = [
  {
    quote:"Hybrid search (BM25 + Vector + RRF) finds the exact clause across thousands of contracts. The AI clause detection is remarkably accurate.",
    name:"Hybrid Search", role:"BM25 + Vector + RRF", company:"Real AI capability",
    avatar:"🔎",
  },
  {
    quote:"25 clause types extracted automatically — liability caps, SLA credits, payment terms, IP ownership, auto-renewal, and more.",
    name:"Clause Extraction", role:"25+ clause types", company:"Real AI capability",
    avatar:"📄",
  },
  {
    quote:"25+ clause types extracted: liability caps, payment terms, SLA credits, renewal dates, IP ownership, and party identifiers across 8 countries.",
    name:"AI Copilot", role:"Citation-verified answers", company:"Real AI capability",
    avatar:"💬",
  },
];

// ── Input field with validation ───────────────────────────────────────────────
function Field({
  label, type="text", value, onChange, error, placeholder, autoFocus=false,
  hint, rightElement,
}: {
  label:string; type?:string; value:string;
  onChange:(v:string)=>void; error?:string;
  placeholder?:string; autoFocus?:boolean;
  hint?:string; rightElement?:React.ReactNode;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{marginBottom:error?8:16}}>
      <label style={{fontSize:13,fontWeight:600,color:C.heading,
        display:"block",marginBottom:6}}>{label}</label>
      <div style={{position:"relative"}}>
        <input
          type={type} value={value} autoFocus={autoFocus}
          onChange={e=>onChange(e.target.value)}
          onFocus={()=>setFocused(true)}
          onBlur={()=>setFocused(false)}
          placeholder={placeholder}
          style={{
            width:"100%", boxSizing:"border-box",
            padding:rightElement?"12px 40px 12px 14px":"12px 14px",
            border:`1.5px solid ${error?C.error:focused?C.primary:C.border}`,
            borderRadius:10, fontSize:14, color:C.heading,
            background:C.surface, outline:"none",
            transition:"border-color 0.15s",
          }}
        />
        {rightElement && (
          <div style={{position:"absolute",right:12,top:"50%",
            transform:"translateY(-50%)",display:"flex",alignItems:"center"}}>
            {rightElement}
          </div>
        )}
      </div>
      {error && (
        <div style={{fontSize:11,color:C.error,marginTop:4,
          display:"flex",alignItems:"center",gap:4}}>
          ⚠️ {error}
        </div>
      )}
      {hint && !error && (
        <div style={{fontSize:11,color:C.muted,marginTop:4}}>{hint}</div>
      )}
    </div>
  );
}

function LoginPageInner() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const isSignup     = searchParams.get("signup") === "true";
  const plan         = searchParams.get("plan");

  const { login, register, user, isLoading } = useAuthStore();
  const [mode, setMode] = useState<"login"|"register">(isSignup?"register":"login");
  const [error, setError]         = useState("");
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [fullName, setFullName]   = useState("");
  const [orgName, setOrgName]     = useState("");
  const [showPw, setShowPw]       = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [testimonialIdx, setTestimonialIdx] = useState(0);
  const [fieldErrors, setFieldErrors] = useState<Record<string,string>>({});

  useEffect(()=>{ if(user) router.push("/dashboard"); },[user,router]);

  // Rotate testimonials
  useEffect(()=>{
    const timer = setInterval(()=>
      setTestimonialIdx(i=>(i+1)%TESTIMONIALS.length), 4000);
    return ()=>clearInterval(timer);
  },[]);

  const validate = (): boolean => {
    const errs: Record<string,string> = {};
    if (!email) errs.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(email)) errs.email = "Enter a valid email address";
    if (!password) errs.password = "Password is required";
    else if (mode==="register" && password.length < 8)
      errs.password = "Password must be at least 8 characters";
    if (mode==="register" && !fullName) errs.fullName = "Full name is required";
    if (mode==="register" && !orgName) errs.orgName = "Organisation name is required";
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (mode==="login") {
        await login(email, password);
      } else {
        await register({ email, password, full_name:fullName, org_name:orgName,
                         ...(plan ? {plan} : {}) });
      }
      router.push("/dashboard");
    } catch(err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong";
      setError(msg);
    } finally { setSubmitting(false); }
  };

  const testimonial = TESTIMONIALS[testimonialIdx];

  return (
    <div style={{display:"flex",height:"100vh",overflow:"hidden",fontFamily:"Inter,system-ui,sans-serif"}}>

      {/* ── Left panel — dark branded ────────────────────────────────────── */}
      <div style={{
        width:"55%", background:C.navy, display:"flex",
        flexDirection:"column", padding:"48px",
        position:"relative", overflow:"hidden",
      }}>
        {/* Background decoration */}
        <div style={{position:"absolute",top:-100,right:-100,width:400,height:400,
          borderRadius:"50%",background:`radial-gradient(circle,${C.primary}15,transparent 70%)`,
          pointerEvents:"none"}}/>
        <div style={{position:"absolute",bottom:-100,left:-50,width:300,height:300,
          borderRadius:"50%",background:`radial-gradient(circle,${C.accent}10,transparent 70%)`,
          pointerEvents:"none"}}/>

        {/* Logo */}
        <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:64}}>
          <svg width="40" height="40" viewBox="0 0 36 36" fill="none">
            <path d="M28 8C24.5 5.5 20 4 15 4C8.4 4 3 9.4 3 18s5.4 14 12 14c5 0 9.5-1.5 13-4"
              stroke="url(#lg1)" strokeWidth="4" strokeLinecap="round" fill="none"/>
            <circle cx="28" cy="8" r="2.5" fill={C.accent}/>
            <circle cx="28" cy="28" r="2.5" fill={C.accent}/>
            <line x1="28" y1="8" x2="33" y2="8" stroke={C.accent} strokeWidth="1.5"/>
            <circle cx="33" cy="8" r="1.5" fill={C.accent}/>
            <line x1="28" y1="28" x2="33" y2="28" stroke={C.accent} strokeWidth="1.5"/>
            <circle cx="33" cy="28" r="1.5" fill={C.accent}/>
            <rect x="11" y="11" width="11" height="14" rx="1.5"
              fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.15)" strokeWidth="0.75"/>
            <line x1="13" y1="15" x2="20" y2="15" stroke="rgba(255,255,255,0.3)" strokeWidth="0.75"/>
            <line x1="13" y1="18" x2="20" y2="18" stroke="rgba(255,255,255,0.3)" strokeWidth="0.75"/>
            <line x1="13" y1="21" x2="18" y2="21" stroke={C.accent} strokeWidth="0.75"/>
            <defs>
              <linearGradient id="lg1" x1="3" y1="4" x2="28" y2="32" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor={C.primary}/>
                <stop offset="100%" stopColor={C.accent}/>
              </linearGradient>
            </defs>
          </svg>
          <div>
            <div style={{color:"white",fontWeight:800,fontSize:20,letterSpacing:"-0.01em"}}>
              <span style={{color:C.accent}}>C</span>laustor
            </div>
            <div style={{fontSize:10,color:"rgba(255,255,255,0.35)",letterSpacing:"0.06em"}}>
              AI Contract Intelligence
            </div>
          </div>
        </div>

        {/* Headline */}
        <div style={{flex:1}}>
          <div style={{fontSize:11,fontWeight:700,color:C.accent,
            letterSpacing:"0.1em",textTransform:"uppercase",marginBottom:12}}>
            AI-Powered Contract Intelligence
          </div>
          <h1 style={{fontSize:36,fontWeight:900,color:"white",
            lineHeight:1.15,letterSpacing:"-0.02em",marginBottom:32}}>
            Review contracts{" "}
            <span style={{background:`linear-gradient(135deg,${C.primary},${C.accent})`,
              WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>
              Under 60s
            </span>{" "}
            with AI
          </h1>

          {/* Animated stats */}
          <div style={{display:"flex",gap:32,marginBottom:48}}>
            {[
              {value:25, suffix:"+", label:"Clause types extracted"},
              {value:8, suffix:"", label:"Countries supported"},
              {value:8,     suffix:"×", label:"Faster reviews"},
            ].map(s=>(
              <div key={s.label}>
                <div style={{fontSize:28,fontWeight:900,color:"white",
                  letterSpacing:"-0.02em"}}>
                  <Counter target={s.value} suffix={s.suffix}/>
                </div>
                <div style={{fontSize:12,color:"rgba(255,255,255,0.5)",marginTop:2}}>
                  {s.label}
                </div>
              </div>
            ))}
          </div>

          {/* Feature pills */}
          <div style={{display:"flex",flexDirection:"column",gap:12,marginBottom:48}}>
            {[
              {Icon:Zap,    text:"25 clause types extracted in under 60 seconds"},
              {Icon:Shield, text:"Bank-grade encryption & org-level data isolation"},
              {Icon:Clock,  text:"Review workflow with SLA tracking & audit log"},
            ].map(f=>(
              <div key={f.text} style={{display:"flex",alignItems:"center",gap:10}}>
                <div style={{width:28,height:28,borderRadius:8,flexShrink:0,
                  background:`${C.primary}20`,border:`1px solid ${C.primary}30`,
                  display:"flex",alignItems:"center",justifyContent:"center"}}>
                  <f.Icon size={13} style={{color:C.accent}}/>
                </div>
                <span style={{fontSize:13,color:"rgba(255,255,255,0.7)",lineHeight:1.4}}>
                  {f.text}
                </span>
              </div>
            ))}
          </div>

          {/* Rotating testimonial */}
          <div style={{padding:"20px 24px",background:"rgba(255,255,255,0.05)",
            border:"1px solid rgba(255,255,255,0.08)",borderRadius:14,
            transition:"opacity 0.3s"}}>
            <div style={{fontSize:13,color:"rgba(255,255,255,0.8)",
              lineHeight:1.7,marginBottom:16,fontStyle:"italic"}}>
              "{testimonial.quote}"
            </div>
            <div style={{display:"flex",alignItems:"center",gap:10}}>
              <div style={{width:36,height:36,borderRadius:"50%",
                background:`linear-gradient(135deg,${C.primary},${C.accent})`,
                display:"flex",alignItems:"center",justifyContent:"center",
                fontSize:12,fontWeight:700,color:"white",flexShrink:0}}>
                {testimonial.avatar}
              </div>
              <div>
                <div style={{fontSize:13,fontWeight:700,color:"white"}}>
                  {testimonial.name}
                </div>
                <div style={{fontSize:11,color:"rgba(255,255,255,0.45)"}}>
                  {testimonial.role}, {testimonial.company}
                </div>
              </div>
              {/* Dots */}
              <div style={{marginLeft:"auto",display:"flex",gap:4}}>
                {TESTIMONIALS.map((_,i)=>(
                  <div key={i} onClick={()=>setTestimonialIdx(i)}
                    style={{width:i===testimonialIdx?16:6,height:6,borderRadius:3,
                      background:i===testimonialIdx?C.primary:"rgba(255,255,255,0.2)",
                      cursor:"pointer",transition:"all 0.3s"}}/>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right panel — auth form ──────────────────────────────────────── */}
      <div style={{width:"45%",display:"flex",flexDirection:"column",
        background:C.surface,overflow:"auto"}}>

        {/* Top nav */}
        <div style={{display:"flex",justifyContent:"flex-end",
          padding:"20px 32px",flexShrink:0}}>
          <span style={{fontSize:13,color:C.muted}}>
            {mode==="login"?"Don't have an account?":"Already have an account?"}
            {" "}
            <button onClick={()=>{setMode(mode==="login"?"register":"login");
              setError("");setFieldErrors({});}}
              style={{color:C.primary,fontWeight:700,background:"none",
                border:"none",cursor:"pointer",fontSize:13,padding:0}}>
              {mode==="login"?"Sign up free":"Sign in"}
            </button>
          </span>
        </div>

        {/* Form */}
        <div style={{flex:1,display:"flex",alignItems:"center",
          justifyContent:"center",padding:"0 48px"}}>
          <div style={{width:"100%",maxWidth:380}}>

            {/* Logo mark above form */}
            <div style={{marginBottom:24,display:"flex",alignItems:"center",gap:8}}>
              <div style={{width:32,height:32,borderRadius:8,
                background:`linear-gradient(135deg,${C.primary},${C.accent})`,
                display:"flex",alignItems:"center",justifyContent:"center",
                fontSize:16,fontWeight:900,color:"white"}}>C</div>
              <span style={{fontWeight:800,fontSize:16,color:C.heading}}>Claustor</span>
            </div>

            <h2 style={{fontSize:26,fontWeight:900,color:C.heading,
              letterSpacing:"-0.02em",marginBottom:4}}>
              {mode==="login"?"Welcome back":"Create your account"}
            </h2>
            <p style={{fontSize:14,color:C.muted,marginBottom:28}}>
              {mode==="login"
                ?"Sign in to your Claustor account"
                :"Start reviewing contracts with AI — free for 5 contracts"}
            </p>

            {/* Global error */}
            {error && (
              <div style={{padding:"10px 14px",borderRadius:8,marginBottom:16,
                background:C.errorLight,border:`1px solid ${C.error}30`,
                fontSize:13,color:C.error,display:"flex",alignItems:"center",gap:8}}>
                ⚠️ {error}
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              {/* Register fields */}
              {mode==="register" && (
                <>
                  <Field label="Full Name" value={fullName} onChange={setFullName}
                    error={fieldErrors.fullName} placeholder="Your full name" autoFocus/>
                  <Field label="Organisation Name" value={orgName} onChange={setOrgName}
                    error={fieldErrors.orgName} placeholder="Your company name"
                    hint="This will be your workspace name"/>
                </>
              )}

              {/* Email */}
              <Field label="Email" type="email" value={email} onChange={setEmail}
                error={fieldErrors.email} placeholder="you@company.com"
                autoFocus={mode==="login"}/>

              {/* Password with toggle */}
              <Field label="Password" type={showPw?"text":"password"}
                value={password} onChange={setPassword}
                error={fieldErrors.password}
                placeholder={mode==="login"?"Enter your password":"Min. 8 characters"}
                rightElement={
                  <button type="button" onClick={()=>setShowPw(!showPw)}
                    style={{background:"none",border:"none",cursor:"pointer",
                      color:C.muted,padding:0,display:"flex",alignItems:"center"}}>
                    {showPw ? <EyeOff size={16}/> : <Eye size={16}/>}
                  </button>
                }/>

              {/* Remember me + Forgot password */}
              {mode==="login" && (
                <div style={{display:"flex",justifyContent:"space-between",
                  alignItems:"center",marginBottom:20}}>
                  <label style={{display:"flex",alignItems:"center",gap:8,
                    fontSize:13,color:C.body,cursor:"pointer"}}>
                    <input type="checkbox" checked={rememberMe}
                      onChange={e=>setRememberMe(e.target.checked)}
                      style={{accentColor:C.primary,width:14,height:14}}/>
                    Remember me for 30 days
                  </label>
                  <Link href="/forgot-password"
                    style={{fontSize:13,color:C.primary,fontWeight:600,
                      textDecoration:"none"}}>
                    Forgot password?
                  </Link>
                </div>
              )}

              {/* Submit */}
              <button type="submit" disabled={submitting||isLoading}
                style={{width:"100%",padding:"13px",borderRadius:10,
                  background:submitting||isLoading?"#94A3B8":C.primary,
                  color:"white",border:"none",fontSize:14,fontWeight:700,
                  cursor:submitting||isLoading?"not-allowed":"pointer",
                  transition:"all 0.15s",
                  boxShadow:submitting||isLoading?"none":`0 4px 16px ${C.primary}40`,
                  display:"flex",alignItems:"center",justifyContent:"center",gap:8}}>
                {submitting||isLoading ? (
                  <>
                    <div style={{width:16,height:16,borderRadius:"50%",
                      border:"2px solid rgba(255,255,255,0.3)",
                      borderTopColor:"white",animation:"spin 0.8s linear infinite"}}/>
                    {mode==="login"?"Signing in...":"Creating account..."}
                  </>
                ) : mode==="login" ? "Sign In" : "Create Account →"}
              </button>

              {/* Divider */}
              <div style={{display:"flex",alignItems:"center",gap:12,margin:"20px 0"}}>
                <div style={{flex:1,height:1,background:C.border}}/>
                <span style={{fontSize:12,color:C.muted}}>or continue with</span>
                <div style={{flex:1,height:1,background:C.border}}/>
              </div>

              {/* Google SSO (UI only) */}
              <button type="button"
                onClick={()=>{window.location.href=`${API}/api/v1/sso/login?redirect_uri=${window.location.origin}/auth/callback`}}
                style={{width:"100%",padding:"11px",borderRadius:10,
                  border:`1.5px solid ${C.border}`,background:C.surface,
                  fontSize:13,fontWeight:600,color:C.heading,cursor:"pointer",
                  display:"flex",alignItems:"center",justifyContent:"center",gap:10,
                  transition:"all 0.15s"}}
                onMouseEnter={e=>{(e.currentTarget as HTMLElement).style.borderColor=C.primary;}}
                onMouseLeave={e=>{(e.currentTarget as HTMLElement).style.borderColor=C.border;}}>
                <svg width="16" height="16" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>
            </form>

            <p style={{fontSize:11,color:C.muted,textAlign:"center",marginTop:24,lineHeight:1.5}}>
              By {mode==="login"?"signing in":"creating an account"}, you agree to our{" "}
              <Link href="/terms" style={{color:C.primary,textDecoration:"none"}}>Terms</Link>
              {" & "}
              <Link href="/privacy" style={{color:C.primary,textDecoration:"none"}}>Privacy Policy</Link>
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        * { box-sizing: border-box; margin: 0; padding: 0; }
      `}</style>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div style={{display:"flex",alignItems:"center",justifyContent:"center",minHeight:"100vh"}}>Loading...</div>}>
      <LoginPageInner />
    </Suspense>
  );
}
