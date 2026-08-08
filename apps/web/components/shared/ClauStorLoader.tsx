"use client";

interface ClauStorLoaderProps {
  size?: number;
  text?: string;
  fullPage?: boolean;
}

export function ClauStorLoader({ size = 44, text = "LOADING", fullPage = false }: ClauStorLoaderProps) {
  const s = size;
  const inner = (
    <div style={{ textAlign: "center" }}>
      <div style={{ position: "relative", width: s, height: s, margin: "0 auto 14px" }}>
        <div style={{
          position: "absolute", inset: 0, borderRadius: "50%",
          border: `${Math.round(s*0.07)}px solid #EFF6FF`,
          borderTopColor: "#0066FF",
          animation: "csp 1s linear infinite",
        }} />
        <div style={{
          position: "absolute",
          inset: Math.round(s*0.14),
          borderRadius: "50%",
          border: `${Math.round(s*0.05)}px solid #DBEAFE`,
          borderBottomColor: "#60A5FA",
          animation: "csp 0.7s linear infinite reverse",
        }} />
        <div style={{
          position: "absolute",
          inset: Math.round(s*0.36),
          borderRadius: "50%",
          background: "#0066FF",
          animation: "cpp 1s ease-in-out infinite",
        }} />
      </div>
      {text && (
        <div style={{
          fontSize: 11, color: "#94A3B8", fontWeight: 700,
          letterSpacing: "0.08em",
        }}>{text}</div>
      )}
      <style>{`
        @keyframes csp { to { transform: rotate(360deg); } }
        @keyframes cpp { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.6;transform:scale(0.85)} }
      `}</style>
    </div>
  );

  if (fullPage) {
    return (
      <div style={{
        position: "fixed", inset: 0, zIndex: 9999,
        background: "white",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {inner}
      </div>
    );
  }

  return inner;
}
