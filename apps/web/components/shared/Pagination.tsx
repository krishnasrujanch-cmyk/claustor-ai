"use client";
import { C } from "@/lib/design-tokens";

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPage: (p: number) => void;
}

export function Pagination({ page, totalPages, total, pageSize, onPage }: PaginationProps) {
  if (totalPages <= 1) return null;

  const start = (page - 1) * pageSize + 1;
  const end   = Math.min(page * pageSize, total);

  // Build page numbers to show
  const pages: (number|"...")[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push("...");
    for (let i = Math.max(2, page-1); i <= Math.min(totalPages-1, page+1); i++) pages.push(i);
    if (page < totalPages - 2) pages.push("...");
    pages.push(totalPages);
  }

  const btn = (label: string|number, onClick: ()=>void, active=false, disabled=false) => (
    <button key={`${label}-${active}`} onClick={onClick} disabled={disabled}
      style={{
        padding:"6px 12px", fontSize:13, fontWeight:active?700:400,
        background: active ? C.primary : C.surface,
        color: active ? "white" : disabled ? "#D1D5DB" : C.muted,
        border:`1px solid ${active ? C.primary : C.border}`,
        borderRadius:6, cursor:disabled?"not-allowed":"pointer",
        minWidth:36,
      }}>
      {label}
    </button>
  );

  return (
    <div style={{display:"flex", alignItems:"center", justifyContent:"space-between",
      padding:"16px 20px", borderTop:`1px solid ${C.border}`}}>
      <span style={{fontSize:13, color:C.muted}}>
        Showing {start}–{end} of {total}
      </span>
      <div style={{display:"flex", gap:4}}>
        {btn("←", () => onPage(page-1), false, page===1)}
        {pages.map((p, i) =>
          p === "..." ? (
            <span key={`dots-${i}`} style={{padding:"6px 4px",color:C.muted}}>…</span>
          ) : (
            btn(p, () => onPage(p as number), p === page)
          )
        )}
        {btn("→", () => onPage(page+1), false, page===totalPages)}
      </div>
    </div>
  );
}
