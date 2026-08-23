"use client";
import { API_URL as API } from "@/lib/config";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import {
  Search, FileText, Users, AlertTriangle, Sparkles,
  Clock, ArrowRight, X, Hash, TrendingUp, Calendar
} from "lucide-react";



// ── Types ─────────────────────────────────────────────────────────────────────
type SuggestionCategory = "contracts" | "counterparties" | "risks" | "ai" | "recent";

interface Suggestion {
  id: string;
  category: SuggestionCategory;
  label: string;
  sub?: string;
  href?: string;
  query?: string;   // for AI suggestions → opens copilot
  icon?: string;
}

// ── Category config ────────────────────────────────────────────────────────────
const CAT_META: Record<SuggestionCategory, { label: string; Icon: any; color: string }> = {
  recent:       { label: "Recent Searches",  Icon: Clock,         color: "#6B7280" },
  contracts:    { label: "Contracts",        Icon: FileText,      color: "#0066FF" },
  counterparties:{ label: "Counterparties",  Icon: Users,         color: "#8B5CF6" },
  risks:        { label: "Risks",            Icon: AlertTriangle, color: "#F59E0B" },
  ai:           { label: "Ask AI",           Icon: Sparkles,      color: "#14B8A6" },
};

// ── Static AI suggestion templates ────────────────────────────────────────────
function buildAiSuggestions(term: string): Suggestion[] {
  // Capitalize first letter of search term
  const t = term.trim();
  const T = t ? t.charAt(0).toUpperCase() + t.slice(1) : t;
  if (!t) return [
    { id:"ai-1", category:"ai", label:"Show all high-risk contracts",      query:"Show all high-risk contracts" },
    { id:"ai-2", category:"ai", label:"Contracts expiring in 90 days",     query:"Which contracts expire in the next 90 days?" },
    { id:"ai-3", category:"ai", label:"Compare payment terms across contracts", query:"Compare payment terms across all contracts" },
  ];
  return [
    { id:"ai-s1", category:"ai", label:`Show ${T} contracts expiring this year`, query:`Show ${T} contracts expiring this year` },
    { id:"ai-s2", category:"ai", label:`Compare ${T} agreements`,                query:`Compare all ${T} agreements` },
    { id:"ai-s3", category:"ai", label:`High-risk clauses in ${T} contracts`,    query:`What are the high-risk clauses in ${T} contracts?` },
  ];
}

// ── Local storage helpers ──────────────────────────────────────────────────────
const HISTORY_KEY = "claustor-search-history";
const getHistory = (): string[] => {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; }
};
const addHistory = (q: string) => {
  if (!q.trim()) return;
  const h = getHistory().filter(x => x !== q).slice(0, 4);
  localStorage.setItem(HISTORY_KEY, JSON.stringify([q, ...h]));
};

// ── Main Component ─────────────────────────────────────────────────────────────
export function CommandPalette() {
  const router = useRouter();
  const { token } = useAuthStore();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(0);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // ── Open / close ─────────────────────────────────────────────────────────────
  const openPalette = useCallback(() => {
    setOpen(true);
    setQuery("");
    setFocused(0);
    setSuggestions(buildDefaultSuggestions());
    setTimeout(() => inputRef.current?.focus(), 30);
  }, []);

  const closePalette = useCallback(() => {
    setOpen(false);
    setQuery("");
    setSuggestions([]);
  }, []);

  // ── Keyboard shortcut ─────────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        open ? closePalette() : openPalette();
      }
      if (e.key === "Escape" && open) closePalette();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, openPalette, closePalette]);

  // ── Default suggestions (empty state) ────────────────────────────────────────
  function buildDefaultSuggestions(): Suggestion[] {
    const history = getHistory();
    const recents: Suggestion[] = history.map((q, i) => ({
      id: `rec-${i}`, category: "recent" as SuggestionCategory,
      label: q, query: q,
    }));
    // Only show recent section if history exists
    // Show different default AI suggestions
    const defaultAi: Suggestion[] = [
      { id:"ai-d1", category:"ai", label:"Show all high-risk contracts",         query:"Show all high-risk contracts" },
      { id:"ai-d2", category:"ai", label:"Contracts expiring in 90 days",        query:"Which contracts expire in the next 90 days?" },
      { id:"ai-d3", category:"ai", label:"Compare payment terms across contracts",query:"Compare payment terms across all contracts" },
      { id:"ai-d4", category:"ai", label:"List contracts above ₹1 crore",        query:"List all contracts above 1 crore value" },
    ];
    return [...recents, ...defaultAi];
  }

  // ── Search API ────────────────────────────────────────────────────────────────
  const search = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSuggestions(buildDefaultSuggestions());
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`${API}/api/v1/contracts/search-suggestions?q=${encodeURIComponent(q)}&limit=5`, { headers });
      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();

      const results: Suggestion[] = [];

      // Contracts
      (data.contracts || []).forEach((c: any, i: number) => {
        results.push({
          id: `c-${i}`, category: "contracts",
          label: c.title, sub: c.counterparty || c.contract_type,
          href: `/dashboard/contracts/${c.id}`,
        });
      });

      // Counterparties
      (data.counterparties || []).forEach((cp: string, i: number) => {
        results.push({
          id: `cp-${i}`, category: "counterparties",
          label: cp,
          href: `/dashboard/contracts?counterparty=${encodeURIComponent(cp)}`,
        });
      });

      // Risk flags
      (data.risks || []).forEach((r: any, i: number) => {
        results.push({
          id: `r-${i}`, category: "risks",
          label: r.label, sub: r.contract,
          href: r.href,
        });
      });

      // AI suggestions
      results.push(...buildAiSuggestions(q));
      setSuggestions(results);
    } catch {
      // Fallback: local AI suggestions only
      setSuggestions(buildAiSuggestions(q));
    } finally {
      setLoading(false);
    }
  }, [token]);

  // ── Debounced search ──────────────────────────────────────────────────────────
  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(query), 220);
    return () => clearTimeout(debounceRef.current);
  }, [query, search]);

  // ── Keyboard navigation ───────────────────────────────────────────────────────
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setFocused(f => Math.min(f + 1, suggestions.length - 1)); }
    if (e.key === "ArrowUp")   { e.preventDefault(); setFocused(f => Math.max(f - 1, 0)); }
    if (e.key === "Enter")     { e.preventDefault(); activateSuggestion(suggestions[focused]); }
    if (e.key === "Escape")    { closePalette(); }
  };

  // ── Activate ──────────────────────────────────────────────────────────────────
  const activateSuggestion = (s: Suggestion | undefined) => {
    if (!s) return;
    addHistory(s.label);
    if (s.category === "ai" && s.query) {
      // Open copilot with pre-filled query
      closePalette();
      router.push(`/dashboard/copilot?q=${encodeURIComponent(s.query!)}`);
    } else if (s.category === "recent" && s.query) {
      // Re-run the search
      setQuery(s.query);
      setFocused(0);
    } else if (s.href) {
      closePalette();
      router.push(s.href);
    }
  };

  // ── Group suggestions by category ─────────────────────────────────────────────
  const grouped = suggestions.reduce<Record<string, Suggestion[]>>((acc, s) => {
    if (!acc[s.category]) acc[s.category] = [];
    acc[s.category].push(s);
    return acc;
  }, {});

  const flatList = suggestions; // for keyboard index

  // ── Scroll focused item into view ─────────────────────────────────────────────
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${focused}"]`) as HTMLElement;
    el?.scrollIntoView({ block: "nearest" });
  }, [focused]);

  if (!open) return (
    <button
      onClick={openPalette}
      style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "6px 12px", borderRadius: 10,
        background: "#F1F5F9", border: "1px solid #E2E8F0",
        color: "#94A3B8", fontSize: 13, cursor: "pointer",
        transition: "all 0.15s", minWidth: 200,
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLElement).style.background = "#E8EEF7";
        (e.currentTarget as HTMLElement).style.borderColor = "#CBD5E1";
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLElement).style.background = "#F1F5F9";
        (e.currentTarget as HTMLElement).style.borderColor = "#E2E8F0";
      }}
    >
      <Search size={14} />
      <span style={{ flex: 1, textAlign: "left" }}>Search contracts, clauses...</span>
      <div style={{ display: "flex", gap: 2 }}>
        <kbd style={{
          padding: "1px 5px", fontSize: 10, fontWeight: 600,
          background: "white", border: "1px solid #E2E8F0",
          borderRadius: 4, color: "#64748B", boxShadow: "0 1px 0 #CBD5E1",
        }}>⌘</kbd>
        <kbd style={{
          padding: "1px 5px", fontSize: 10, fontWeight: 600,
          background: "white", border: "1px solid #E2E8F0",
          borderRadius: 4, color: "#64748B", boxShadow: "0 1px 0 #CBD5E1",
        }}>K</kbd>
      </div>
    </button>
  );

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={closePalette}
        style={{
          position: "fixed", inset: 0, zIndex: 998,
          background: "rgba(15,23,42,0.6)",
          backdropFilter: "blur(4px)",
          animation: "fadeIn 0.12s ease",
        }}
      />

      {/* Palette */}
      <div style={{
        position: "fixed", top: "14%", left: "50%",
        transform: "translateX(-50%)",
        width: "100%", maxWidth: 560,
        background: "white", borderRadius: 16,
        boxShadow: "0 24px 80px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.05)",
        zIndex: 999, overflow: "hidden",
        animation: "slideDown 0.15s ease",
      }}>

        {/* Search input */}
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "14px 16px",
          borderBottom: "1px solid #F1F5F9",
        }}>
          {loading
            ? <div style={{
                width: 16, height: 16, borderRadius: "50%",
                border: "2px solid #E2E8F0", borderTopColor: "#0066FF",
                animation: "spin 0.6s linear infinite", flexShrink: 0,
              }} />
            : <Search size={16} color="#94A3B8" style={{ flexShrink: 0 }} />
          }
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setFocused(0); }}
            onKeyDown={handleKey}
            placeholder="Search contracts, clauses, or ask AI anything..."
            style={{
              flex: 1, border: "none", outline: "none",
              fontSize: 14, color: "#111827", background: "transparent",
            }}
            spellCheck={false}
            autoComplete="off"
          />
          {query && (
            <button onClick={() => { setQuery(""); setSuggestions(buildDefaultSuggestions()); setFocused(0); inputRef.current?.focus(); }}
              style={{ background: "none", border: "none", cursor: "pointer", color: "#94A3B8", padding: 2, borderRadius: 4 }}>
              <X size={14} />
            </button>
          )}
          <kbd onClick={closePalette} style={{
            padding: "2px 6px", fontSize: 10, fontWeight: 600,
            background: "#F1F5F9", border: "1px solid #E2E8F0",
            borderRadius: 5, color: "#94A3B8", cursor: "pointer",
          }}>ESC</kbd>
        </div>

        {/* Results */}
        <div ref={listRef} style={{ maxHeight: 400, overflowY: "auto", padding: "8px 0" }}>
          {suggestions.length === 0 && !loading && (
            <div style={{ padding: "32px 20px", textAlign: "center", color: "#94A3B8", fontSize: 13 }}>
              No results for "{query}"
            </div>
          )}

          {(["recent", "contracts", "counterparties", "risks", "ai"] as SuggestionCategory[]).map(cat => {
            const items = grouped[cat];
            if (!items?.length) return null;
            const meta = CAT_META[cat];
            const CatIcon = meta.Icon;

            return (
              <div key={cat}>
                {/* Category header */}
                <div style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "6px 16px 4px",
                }}>
                  <CatIcon size={11} color={meta.color} />
                  <span style={{
                    fontSize: 10, fontWeight: 700, color: "#94A3B8",
                    textTransform: "uppercase", letterSpacing: "0.08em",
                  }}>{meta.label}</span>
                  {cat === "ai" && (
                    <span style={{
                      marginLeft: 4, fontSize: 9, fontWeight: 700,
                      padding: "1px 5px", borderRadius: 4,
                      background: "#F0FDFA", color: "#14B8A6",
                      border: "1px solid #CCFBF1",
                    }}>Powered by Judge AI</span>
                  )}
                </div>

                {/* Items */}
                {items.map(s => {
                  const idx = flatList.findIndex(x => x.id === s.id);
                  const isActive = idx === focused;
                  const CatIconSmall = meta.Icon;
                  return (
                    <div
                      key={s.id}
                      data-idx={idx}
                      onClick={() => activateSuggestion(s)}
                      onMouseEnter={() => setFocused(idx)}
                      style={{
                        display: "flex", alignItems: "center", gap: 10,
                        padding: "8px 16px", cursor: "pointer",
                        background: isActive ? "#EFF6FF" : "transparent",
                        borderLeft: isActive ? `2px solid #0066FF` : "2px solid transparent",
                        transition: "all 0.08s",
                      }}
                    >
                      <div style={{
                        width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                        background: isActive ? "#DBEAFE" : "#F8FAFC",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        border: "1px solid",
                        borderColor: isActive ? "#BFDBFE" : "#F1F5F9",
                      }}>
                        {cat === "ai"
                          ? <Sparkles size={13} color="#14B8A6" />
                          : cat === "recent"
                          ? <Clock size={13} color="#94A3B8" />
                          : <CatIconSmall size={13} color={isActive ? "#0066FF" : meta.color} />
                        }
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: 13, fontWeight: 500,
                          color: isActive ? "#0066FF" : "#111827",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}>{s.label}</div>
                        {s.sub && (
                          <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 1 }}>{s.sub}</div>
                        )}
                      </div>
                      <ArrowRight size={13} color={isActive ? "#0066FF" : "#CBD5E1"} />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div style={{
          display: "flex", alignItems: "center", gap: 16,
          padding: "8px 16px",
          borderTop: "1px solid #F1F5F9",
          background: "#FAFBFC",
        }}>
          {[
            { key: "↑↓", label: "navigate" },
            { key: "↵", label: "select" },
            { key: "ESC", label: "close" },
          ].map(({ key, label }) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <kbd style={{
                padding: "1px 5px", fontSize: 10, fontWeight: 600,
                background: "white", border: "1px solid #E2E8F0",
                borderRadius: 4, color: "#64748B", boxShadow: "0 1px 0 #CBD5E1",
              }}>{key}</kbd>
              <span style={{ fontSize: 11, color: "#94A3B8" }}>{label}</span>
            </div>
          ))}
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 11, color: "#CBD5E1" }}>
            Claustor AI Search
          </span>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity:0 } to { opacity:1 } }
        @keyframes slideDown { from { opacity:0; transform:translateX(-50%) translateY(-8px) } to { opacity:1; transform:translateX(-50%) translateY(0) } }
        @keyframes spin { to { transform:rotate(360deg) } }
      `}</style>
    </>
  );
}
