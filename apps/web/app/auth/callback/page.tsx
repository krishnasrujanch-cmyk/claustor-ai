"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API_URL as API } from "@/lib/config";
import { useAuthStore } from "@/store/auth";
import { ClauStorLoader } from "@/components/shared/ClauStorLoader";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const { setAuth } = useAuthStore();

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const errorParam = searchParams.get("error");

    if (errorParam) {
      setError(searchParams.get("error_description") || "Authentication failed");
      return;
    }

    if (!code) {
      setError("No authorization code received");
      return;
    }

    fetch(`${API}/api/v1/sso/callback?code=${code}&state=${state || ""}`)
      .then(r => {
        if (!r.ok) throw new Error("Authentication failed");
        return r.json();
      })
      .then(data => {
        if (data.access_token) {
          localStorage.setItem("token", data.access_token);
          if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);
          setAuth({ token: data.access_token, user: data.user });
          router.push("/dashboard");
        } else {
          setError("No token received");
        }
      })
      .catch(err => setError(err.message));
  }, [searchParams, router, setAuth]);

  if (error) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center", flexDirection: "column", gap: 16 }}>
        <div style={{ fontSize: 48 }}>⚠️</div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#DC2626" }}>Authentication Failed</h2>
        <p style={{ color: "#64748B", fontSize: 14 }}>{error}</p>
        <button onClick={() => router.push("/login")}
          style={{ padding: "10px 24px", borderRadius: 8, background: "#5B4BFF",
            color: "white", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600 }}>
          Back to Login
        </button>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", flexDirection: "column", gap: 16 }}>
      <ClauStorLoader />
      <p style={{ color: "#64748B", fontSize: 14 }}>Completing sign-in...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center" }}>
        <ClauStorLoader />
      </div>
    }>
      <CallbackHandler />
    </Suspense>
  );
}
