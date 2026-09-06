"use client";
import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { API_URL as API } from "@/lib/config";

const C = {
  primary: "#0066FF",
  primaryDark: "#0052CC",
  heading: "#111827",
  body: "#374151",
  muted: "#6B7280",
  border: "#E5E7EB",
  surface: "#FFFFFF",
  bg: "#FAFBFC",
  error: "#EF4444",
  success: "#22C55E",
};

function ResetForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (!token) {
      setError("Invalid or missing reset token.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || "Reset failed. The link may have expired.");
      }

      setSuccess(true);
      setTimeout(() => router.push("/login"), 3000);
    } catch (err: any) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div style={{ textAlign: "center" }}>
        <h2 style={{ color: C.heading, fontSize: 20, fontWeight: 700, marginBottom: 12 }}>
          Invalid reset link
        </h2>
        <p style={{ color: C.muted, fontSize: 14, marginBottom: 20 }}>
          This link is invalid or has expired. Please request a new one.
        </p>
        <Link href="/forgot-password" style={{
          display: "inline-block",
          background: C.primary,
          color: "white",
          padding: "12px 24px",
          borderRadius: 10,
          fontWeight: 700,
          fontSize: 14,
          textDecoration: "none",
        }}>
          Request new link
        </Link>
      </div>
    );
  }

  return success ? (
    <div style={{ textAlign: "center" }}>
      <div style={{
        width: 56, height: 56, borderRadius: "50%",
        background: "#ECFDF5", display: "flex",
        alignItems: "center", justifyContent: "center",
        margin: "0 auto 20px",
      }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
          stroke={C.success} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <h2 style={{ color: C.heading, fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
        Password reset
      </h2>
      <p style={{ color: C.muted, fontSize: 14, marginBottom: 20 }}>
        Your password has been updated. Redirecting to login...
      </p>
    </div>
  ) : (
    <>
      <h2 style={{
        color: C.heading, fontSize: 20, fontWeight: 700,
        marginBottom: 8, textAlign: "center",
      }}>
        Set new password
      </h2>
      <p style={{
        color: C.muted, fontSize: 14, textAlign: "center",
        marginBottom: 28, lineHeight: 1.5,
      }}>
        Enter your new password below.
      </p>

      <form onSubmit={handleSubmit}>
        <label style={{ display: "block", marginBottom: 6, fontSize: 13, fontWeight: 600, color: C.body }}>
          New password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 8 characters"
          required
          minLength={8}
          style={{
            width: "100%", padding: "12px 14px", borderRadius: 10,
            border: `1px solid ${C.border}`, fontSize: 14,
            outline: "none", marginBottom: 16, boxSizing: "border-box",
          }}
        />

        <label style={{ display: "block", marginBottom: 6, fontSize: 13, fontWeight: 600, color: C.body }}>
          Confirm password
        </label>
        <input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Re-enter password"
          required
          style={{
            width: "100%", padding: "12px 14px", borderRadius: 10,
            border: `1px solid ${C.border}`, fontSize: 14,
            outline: "none", marginBottom: 16, boxSizing: "border-box",
          }}
        />

        {error && (
          <p style={{ color: C.error, fontSize: 13, marginBottom: 12 }}>{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%", padding: 13, borderRadius: 10,
            background: loading ? "#94A3B8" : C.primary,
            color: "white", border: "none", fontSize: 14,
            fontWeight: 700, cursor: loading ? "not-allowed" : "pointer",
            marginBottom: 20,
          }}
        >
          {loading ? "Resetting..." : "Reset password"}
        </button>
      </form>
    </>
  );
}

export default function ResetPasswordPage() {
  return (
    <div style={{
      minHeight: "100vh", background: C.bg,
      display: "flex", alignItems: "center",
      justifyContent: "center", padding: 20,
    }}>
      <div style={{
        width: "100%", maxWidth: 420, background: C.surface,
        borderRadius: 16, border: `1px solid ${C.border}`,
        padding: 40, boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
      }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <Link href="/" style={{ textDecoration: "none" }}>
            <span style={{ fontSize: 24, fontWeight: 800, color: C.heading, letterSpacing: "-0.5px" }}>
              Clau<span style={{ color: C.primary }}>stor</span>
            </span>
          </Link>
        </div>
        <Suspense fallback={<p style={{ textAlign: "center", color: C.muted }}>Loading...</p>}>
          <ResetForm />
        </Suspense>
      </div>
    </div>
  );
}
