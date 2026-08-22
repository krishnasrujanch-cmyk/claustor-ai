"use client";
export const dynamic = "force-dynamic";
import { useEffect } from "react";
import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function RegisterPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const plan = searchParams.get("plan");

  useEffect(()=>{
    const params = new URLSearchParams({ signup:"true" });
    if (plan) params.set("plan", plan);
    router.replace(`/login?${params.toString()}`);
  },[]);

  return (
    <div style={{height:"100vh",display:"flex",alignItems:"center",
      justifyContent:"center",fontFamily:"Inter,system-ui,sans-serif"}}>
      <div style={{textAlign:"center",color:"#6B7280"}}>
        <div style={{width:32,height:32,borderRadius:"50%",
          border:"2px solid #0066FF",borderTopColor:"transparent",
          animation:"spin 0.8s linear infinite",margin:"0 auto 12px"}}/>
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div style={{display:"flex",alignItems:"center",justifyContent:"center",minHeight:"100vh"}}>Loading...</div>}>
      <RegisterPageInner />
    </Suspense>
  );
}
