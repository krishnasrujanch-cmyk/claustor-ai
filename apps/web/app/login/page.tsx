"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/auth";

const C = {
  primary: "#5B4BFF",
  primaryHover: "#4C3FE0",
  primaryLight: "#EEF0FF",
  heading: "#111827",
  body: "#374151",
  muted: "#6B7280",
  border: "#E5E7EB",
  error: "#EF4444",
  surface: "#FFFFFF",
  bg: "#FAFBFC",
};

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isSignup = searchParams.get("signup") === "true";
  const plan = searchParams.get("plan");

  const { login, register, user, isLoading } = useAuthStore();
  const [mode, setMode] = useState<"login" | "register">(
    isSignup ? "register" : "login"
  );
  const [error, setError] = useState("");

  // Form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");

  // Redirect if already logged in
  useEffect(() => {
    if (user) router.push("/dashboard");
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register({ email, password, full_name: fullName, org_name: orgName });
      }
      router.push("/dashboard");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong";
      setError(message);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: C.bg,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Top bar */}
      <div
        style={{
          padding: "16px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Link
          href="/"
          style={{
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: C.primary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
              fontWeight: 700,
              fontSize: 16,
            }}
          >
            C
          </div>
          <span style={{ fontWeight: 700, fontSize: 18, color: C.heading }}>
            Claustor
          </span>
        </Link>

        <span style={{ fontSize: 14, color: C.muted }}>
          {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          <button
            onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
            style={{
              background: "none",
              border: "none",
              color: C.primary,
              fontWeight: 600,
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            {mode === "login" ? "Sign up free" : "Sign in"}
          </button>
        </span>
      </div>

      {/* Form */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 24px",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: 420,
            background: C.surface,
            borderRadius: 16,
            padding: 40,
            border: `1px solid ${C.border}`,
            boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
          }}
        >
          {/* Header */}
          <div style={{ marginBottom: 32 }}>
            <h1
              style={{
                fontSize: 24,
                fontWeight: 800,
                color: C.heading,
                marginBottom: 8,
              }}
            >
              {mode === "login" ? "Welcome back" : "Get started free"}
            </h1>
            <p style={{ fontSize: 14, color: C.muted }}>
              {mode === "login"
                ? "Sign in to your Claustor account"
                : "No credit card required · 5 contracts free forever"}
            </p>
            {plan && mode === "register" && (
              <div
                style={{
                  marginTop: 12,
                  padding: "8px 12px",
                  background: C.primaryLight,
                  borderRadius: 8,
                  fontSize: 13,
                  color: C.primary,
                  fontWeight: 600,
                }}
              >
                Starting with {plan.charAt(0).toUpperCase() + plan.slice(1)} plan — 14-day trial
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div
              style={{
                background: "#FEF2F2",
                border: "1px solid #FEE2E2",
                borderRadius: 8,
                padding: "10px 14px",
                fontSize: 14,
                color: C.error,
                marginBottom: 20,
              }}
            >
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {mode === "register" && (
              <>
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: C.body, marginBottom: 6 }}>
                    Full name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Srujan Kumar"
                    required
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: C.body, marginBottom: 6 }}>
                    Organisation name
                  </label>
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="DKU Technologies"
                    required
                    style={inputStyle}
                  />
                </div>
              </>
            )}

            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: C.body, marginBottom: 6 }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                style={inputStyle}
              />
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: C.body }}>Password</label>
                {mode === "login" && (
                  <Link href="/forgot-password" style={{ fontSize: 12, color: C.primary, textDecoration: "none" }}>
                    Forgot password?
                  </Link>
                )}
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "register" ? "Min 8 characters" : "Your password"}
                required
                minLength={mode === "register" ? 8 : 1}
                style={inputStyle}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              style={{
                width: "100%",
                background: isLoading ? "#9CA3AF" : C.primary,
                color: "white",
                border: "none",
                borderRadius: 8,
                padding: "12px 20px",
                fontSize: 15,
                fontWeight: 700,
                cursor: isLoading ? "not-allowed" : "pointer",
                marginTop: 4,
              }}
            >
              {isLoading
                ? "Please wait..."
                : mode === "login"
                ? "Sign in"
                : "Create account"}
            </button>
          </form>

          {/* Divider */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              margin: "24px 0",
            }}
          >
            <div style={{ flex: 1, height: 1, background: C.border }} />
            <span style={{ fontSize: 12, color: C.muted }}>or continue with</span>
            <div style={{ flex: 1, height: 1, background: C.border }} />
          </div>

          {/* SSO buttons */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <a
              href="/api/v1/sso/login?redirect_uri=http://localhost:3000/api/auth/callback"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 10,
                padding: "10px 20px",
                border: `1.5px solid ${C.border}`,
                borderRadius: 8,
                textDecoration: "none",
                fontSize: 14,
                fontWeight: 600,
                color: C.body,
                background: C.surface,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </a>
          </div>

          {/* Terms */}
          {mode === "register" && (
            <p style={{ fontSize: 12, color: C.muted, textAlign: "center", marginTop: 20, lineHeight: 1.5 }}>
              By creating an account you agree to our{" "}
              <Link href="/terms" style={{ color: C.primary }}>Terms</Link>
              {" "}and{" "}
              <Link href="/privacy" style={{ color: C.primary }}>Privacy Policy</Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 14px",
  border: `1.5px solid #E5E7EB`,
  borderRadius: 8,
  fontSize: 14,
  color: "#374151",
  outline: "none",
  background: "white",
  transition: "border-color 0.15s",
};
