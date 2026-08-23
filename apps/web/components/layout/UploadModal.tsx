"use client";
import { API_URL as API } from "@/lib/config";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { X, UploadCloud, FileText, CheckCircle, AlertCircle, Loader } from "lucide-react";



// ── Types ──────────────────────────────────────────────────────────────────
type ModalState = "dropzone" | "processing" | "complete" | "error" | "minimized";

interface ProcessingStep {
  id: string;
  label: string;
  status: "pending" | "active" | "done" | "error";
}

const INITIAL_STEPS: ProcessingStep[] = [
  { id: "parse",   label: "Parsing document and extracting text",    status: "pending" },
  { id: "ocr",     label: "Running OCR and image analysis",          status: "pending" },
  { id: "clauses", label: "Extracting clauses with AI",              status: "pending" },
  { id: "risk",    label: "Scoring risk levels",                     status: "pending" },
  { id: "index",   label: "Indexing for semantic search",            status: "pending" },
  { id: "done",    label: "Finalizing analysis",                     status: "pending" },
];

// ── Status → step mapping ──────────────────────────────────────────────────
function statusToSteps(status: string, steps: ProcessingStep[]): ProcessingStep[] {
  const order = ["parse","ocr","clauses","risk","index","done"];
  const activeIdx: Record<string, number> = {
    queued:    -1,
    parsing:    0,
    extracting: 2,
    scoring:    3,
    indexing:   4,
    analyzed:   5,
    error:      -2,
  };
  const idx = activeIdx[status] ?? -1;
  return steps.map((s, i) => ({
    ...s,
    status: status === "error"
      ? (s.status === "active" ? "error" : s.status)
      : i < idx ? "done"
      : i === idx ? "active"
      : "pending",
  }));
}

// ── Main Component ─────────────────────────────────────────────────────────
interface UploadModalProps {
  onClose: () => void;
  onBackground?: (contractId: string, fileName: string) => void;
}

export function UploadModal({ onClose, onBackground }: UploadModalProps) {
  const router = useRouter();
  const { token } = useAuthStore();
  const [state, setState] = useState<ModalState>("dropzone");
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<ProcessingStep[]>(INITIAL_STEPS);
  const [contractId, setContractId] = useState<string | null>(null);
  const contractIdRef = useRef<string | null>(null);
  const pendingBgRef = useRef<boolean>(false);
  const fileNameRef = useRef<string>("");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();
  const startTimeRef = useRef<number>(0);

  // ── Cleanup ────────────────────────────────────────────────────────────────
  useEffect(() => () => clearInterval(pollRef.current), []);

  // ── Upload ─────────────────────────────────────────────────────────────────
  const upload = useCallback(async (f: File) => {
    if (!f) return;
    setFile(f);
    fileNameRef.current = f.name;
    setState("processing");
    setProgress(5);
    startTimeRef.current = Date.now();

    // Animate first step
    setSteps(prev => prev.map((s, i) => ({ ...s, status: i === 0 ? "active" : "pending" })));

    const formData = new FormData();
    formData.append("file", f);
    formData.append("title", f.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " "));

    try {
      const res = await fetch(`${API}/api/v1/contracts/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      console.log("Upload status:", res.status);
      const rawText = await res.text();
      console.log("Upload raw:", rawText.slice(0,300));
      if (!res.ok) throw new Error("Upload failed: " + rawText.slice(0,100));
      const data = JSON.parse(rawText);
      console.log("Upload response:", JSON.stringify(data));
      const cid = data.contract_id || data.id || data.contract?.id;
      contractIdRef.current = cid;  // set ref FIRST before state
      setContractId(cid);
      // If user already clicked "run in background", fire now
      if (pendingBgRef.current && onBackground && cid) {
        onBackground(cid, fileNameRef.current);
        pendingBgRef.current = false;
      }
      setProgress(15);
      startPolling(cid);
    } catch (e: any) {
      setError(e.message || "Upload failed");
      setState("error");
    }
  }, [token]);

  // ── Poll status ────────────────────────────────────────────────────────────
  const startPolling = (cid: string) => {
    const statusOrder = ["queued","parsing","extracting","scoring","indexing","analyzed"];
    const progressMap: Record<string, number> = {
      queued: 15, parsing: 30, extracting: 55, scoring: 70, indexing: 85, analyzed: 100,
    };

    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/v1/contracts/${cid}/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const data = await res.json();
        const st = data.status || "queued";

        setProgress(progressMap[st] || 15);
        setSteps(prev => statusToSteps(st, prev));

        if (st === "analyzed") {
          clearInterval(pollRef.current);
          setProgress(100);
          setSteps(INITIAL_STEPS.map(s => ({ ...s, status: "done" })));
          // Fetch full contract details for summary
          try {
            const detailRes = await fetch(`${API}/api/v1/contracts/${cid}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            const detail = detailRes.ok ? await detailRes.json() : data;
            setResult(detail);
          } catch { setResult(data); }
          setTimeout(() => setState("complete"), 600);
        } else if (st === "error" || st === "failed") {
          clearInterval(pollRef.current);
          setError("Analysis failed. Please try again.");
          setState("error");
        }
      } catch { /* keep polling */ }
    }, 2000);
  };

  // ── Drag handlers ──────────────────────────────────────────────────────────
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f && (f.type === "application/pdf" || f.name.endsWith(".docx"))) {
      upload(f);
    }
  }, [upload]);

  // ── Paste support ──────────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: ClipboardEvent) => {
      const f = e.clipboardData?.files[0];
      if (f && state === "dropzone") upload(f);
    };
    window.addEventListener("paste", handler);
    return () => window.removeEventListener("paste", handler);
  }, [state, upload]);

  // ── Keyboard close ─────────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const fileSizeMB = file ? (file.size / 1024 / 1024).toFixed(1) : "0";

  return (
    <>
      {/* Backdrop — hidden when minimized */}
      {state !== "minimized" && state !== "complete" && <div onClick={() => setState("minimized")} style={{
        position: "fixed", inset: 0, zIndex: 998,
        background: "rgba(15,23,42,0.65)",
        backdropFilter: "blur(6px)",
        animation: "fadeIn 0.15s ease",
      }} />}

      {/* Modal — hidden when minimized */}
      {state !== "minimized" &&
      <div style={{
        position: "fixed", top: "50%", left: "50%",
        transform: "translate(-50%, -50%)",
        width: "100%", maxWidth: 520,
        background: "white", borderRadius: 20,
        boxShadow: "0 32px 100px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.04)",
        zIndex: 999, overflow: "hidden",
        animation: "slideUp 0.18s ease",
      }}>

        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "18px 20px",
          borderBottom: "1px solid #F1F5F9",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: "linear-gradient(135deg,#0066FF,#06B6D4)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <UploadCloud size={16} color="white" />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#111827" }}>
                Upload & Analyze Contract
              </div>
              <div style={{ fontSize: 11, color: "#94A3B8" }}>
                PDF or DOCX · AES-256 encrypted
              </div>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "#F1F5F9", border: "none", borderRadius: 8,
            width: 28, height: 28, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "#64748B",
          }}>
            <X size={14} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "20px" }}>

          {/* ── STATE 1: DROPZONE ── */}
          {state === "dropzone" && (
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: `2px dashed ${dragOver ? "#0066FF" : "#E2E8F0"}`,
                borderRadius: 16,
                padding: "48px 24px",
                textAlign: "center",
                cursor: "pointer",
                background: dragOver ? "#EFF6FF" : "#FAFBFC",
                transition: "all 0.15s",
              }}
            >
              <div style={{
                width: 56, height: 56, borderRadius: 16, margin: "0 auto 16px",
                background: dragOver ? "#DBEAFE" : "#F1F5F9",
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.15s",
              }}>
                <UploadCloud size={24} color={dragOver ? "#0066FF" : "#94A3B8"} />
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#111827", marginBottom: 6 }}>
                {dragOver ? "Drop to upload" : "Drag & drop your contract"}
              </div>
              <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 16 }}>
                or click to browse · PDF, DOCX supported · Max 50MB
              </div>
              <div style={{ fontSize: 11, color: "#CBD5E1" }}>
                🔒 AES-256 encrypted · Your data stays private
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx"
                style={{ display: "none" }}
                onChange={e => { const f = e.target.files?.[0]; if (f) upload(f); }}
              />
            </div>
          )}

          {/* ── STATE 2: PROCESSING ── */}
          {state === "processing" && file && (
            <>
              {/* File info */}
              <div style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "12px 14px", borderRadius: 12,
                background: "#F8FAFC", border: "1px solid #E2E8F0",
                marginBottom: 16,
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: "#EFF6FF", border: "1px solid #DBEAFE",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  flexShrink: 0,
                }}>
                  <FileText size={20} color="#0066FF" />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 13, fontWeight: 600, color: "#111827",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>{file.name}</div>
                  <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>
                    {fileSizeMB} MB · Analyzing...
                  </div>
                </div>
                <div style={{ fontSize: 18, fontWeight: 800, color: "#0066FF", flexShrink: 0 }}>
                  {progress}%
                </div>
              </div>

              {/* Progress bar */}
              <div style={{
                height: 6, background: "#F1F5F9", borderRadius: 99,
                overflow: "hidden", marginBottom: 16, position: "relative",
              }}>
                <div style={{
                  height: "100%", borderRadius: 99,
                  background: "linear-gradient(90deg, #0066FF, #06B6D4)",
                  width: `${progress}%`,
                  transition: "width 0.5s ease",
                  position: "relative", overflow: "hidden",
                }}>
                  {/* Shimmer */}
                  <div style={{
                    position: "absolute", inset: 0,
                    background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)",
                    animation: "shimmer 1.5s infinite",
                  }} />
                </div>
              </div>

              {/* Live AI log */}
              <div style={{
                background: "#0B0F19", borderRadius: 12,
                padding: "14px 16px",
                border: "1px solid rgba(255,255,255,0.06)",
              }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 6, marginBottom: 12,
                }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: "#0066FF", animation: "pulse 1.5s infinite",
                  }} />
                  <span style={{
                    fontSize: 9, fontWeight: 700, color: "#94A3B8",
                    textTransform: "uppercase", letterSpacing: "0.1em",
                  }}>Live AI Analysis</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {steps.map(step => (
                    <div key={step.id} style={{
                      display: "flex", alignItems: "center", gap: 8,
                      fontFamily: "monospace", fontSize: 11,
                    }}>
                      {step.status === "done" && (
                        <CheckCircle size={13} color="#22C55E" style={{ flexShrink: 0 }} />
                      )}
                      {step.status === "active" && (
                        <div style={{
                          width: 13, height: 13, borderRadius: "50%",
                          border: "2px solid #0066FF",
                          borderTopColor: "transparent",
                          animation: "spin 0.6s linear infinite",
                          flexShrink: 0,
                        }} />
                      )}
                      {step.status === "pending" && (
                        <div style={{
                          width: 13, height: 13, borderRadius: "50%",
                          border: "2px solid rgba(255,255,255,0.1)",
                          flexShrink: 0,
                        }} />
                      )}
                      {step.status === "error" && (
                        <AlertCircle size={13} color="#EF4444" style={{ flexShrink: 0 }} />
                      )}
                      <span style={{
                        color: step.status === "done" ? "#94A3B8"
                          : step.status === "active" ? "white"
                          : step.status === "error" ? "#EF4444"
                          : "rgba(255,255,255,0.2)",
                        fontWeight: step.status === "active" ? 600 : 400,
                      }}>{step.label}</span>
                      {step.status === "active" && (
                        <span style={{
                          marginLeft: "auto", fontSize: 9,
                          color: "#0066FF", fontWeight: 700,
                          animation: "blink 1s infinite",
                        }}>●</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* ── STATE 3: COMPLETE ── */}
          {state === "complete" && result && (
            <div style={{ textAlign: "center" }}>
              {/* Success icon */}
              <div style={{
                width: 64, height: 64, borderRadius: "50%",
                background: "linear-gradient(135deg,#22C55E,#16A34A)",
                display: "flex", alignItems: "center", justifyContent: "center",
                margin: "0 auto 16px",
                boxShadow: "0 8px 24px rgba(34,197,94,0.3)",
                animation: "popIn 0.3s ease",
              }}>
                <CheckCircle size={32} color="white" />
              </div>

              <div style={{ fontSize: 18, fontWeight: 700, color: "#111827", marginBottom: 4 }}>
                Analysis Complete!
              </div>
              <div style={{ fontSize: 13, color: "#64748B", marginBottom: 20 }}>
                {file?.name}
              </div>

              {/* Stats */}
              <div style={{
                display: "grid", gridTemplateColumns: "1fr 1fr 1fr",
                gap: 10, marginBottom: 20,
              }}>
                {[
                  { label: "Clauses", value: result.clause_count || result.total_clauses || "—", color: "#0066FF" },
                  { label: "Risk Level", value: result.risk_level?.toUpperCase() || "—",
                    color: result.risk_level === "high" ? "#EF4444" : result.risk_level === "medium" ? "#F59E0B" : "#22C55E" },
                  { label: "Contract Type", value: result.contract_type || "—", color: "#8B5CF6" },
                ].map(stat => (
                  <div key={stat.label} style={{
                    padding: "12px 8px", borderRadius: 10,
                    background: "#F8FAFC", border: "1px solid #F1F5F9",
                    textAlign: "center",
                  }}>
                    <div style={{ fontSize: 18, fontWeight: 800, color: stat.color }}>
                      {stat.value}
                    </div>
                    <div style={{ fontSize: 10, color: "#94A3B8", marginTop: 2 }}>{stat.label}</div>
                  </div>
                ))}
              </div>

              {/* CTAs */}
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  onClick={() => { onClose(); router.push(`/dashboard/contracts/${contractId}`); }}
                  style={{
                    flex: 2, padding: "12px", borderRadius: 10,
                    background: "#0066FF", color: "white", border: "none",
                    fontSize: 13, fontWeight: 700, cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(0,102,255,0.3)",
                  }}
                >
                  View Contract →
                </button>
                <button
                  onClick={() => { setState("dropzone"); setFile(null); setProgress(0); setSteps(INITIAL_STEPS); setResult(null); setContractId(null); }}
                  style={{
                    flex: 1, padding: "12px", borderRadius: 10,
                    background: "transparent", color: "#64748B",
                    border: "1px solid #E2E8F0", fontSize: 13,
                    cursor: "pointer", fontWeight: 500,
                  }}
                >
                  Upload Another
                </button>
              </div>
            </div>
          )}

          {/* ── STATE 4: ERROR ── */}
          {state === "error" && (
            <div style={{ textAlign: "center", padding: "16px 0" }}>
              <div style={{
                width: 56, height: 56, borderRadius: "50%",
                background: "#FEF2F2", border: "1px solid #FCA5A5",
                display: "flex", alignItems: "center", justifyContent: "center",
                margin: "0 auto 12px",
              }}>
                <AlertCircle size={28} color="#EF4444" />
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#111827", marginBottom: 4 }}>Upload failed</div>
              <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 20 }}>{error}</div>
              <button
                onClick={() => { setState("dropzone"); setFile(null); setProgress(0); setSteps(INITIAL_STEPS); setError(""); }}
                style={{
                  padding: "10px 24px", borderRadius: 10,
                  background: "#0066FF", color: "white", border: "none",
                  fontSize: 13, fontWeight: 600, cursor: "pointer",
                }}
              >
                Try Again
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        {state === "processing" && (
          <div style={{
            padding: "12px 20px",
            borderTop: "1px solid #F1F5F9",
            background: "#FAFBFC",
            display: "flex", justifyContent: "flex-end",
          }}>
            <button
              onClick={() => {
                const cid = contractIdRef.current || contractId;
                setState("minimized");
              }}
              style={{
                padding: "6px 16px", borderRadius: 8,
                background: "transparent", color: "#94A3B8",
                border: "1px solid #E2E8F0", fontSize: 12,
                cursor: "pointer", fontWeight: 500,
              }}
            >
              Minimize
            </button>
            <button
              onClick={() => {
                if (contractId && file && onBackground) {
                  onBackground(contractId, file.name);
                }
                onClose();
              }}
              style={{ display: "none" }} // handled above
            />
          </div>
        )}
      </div>

      }

      {/* Minimized floating card */}
      {state === "minimized" && file && (
        <div style={{
          position: "fixed", bottom: 24, right: 24,
          width: 300, background: "white", borderRadius: 14,
          boxShadow: "0 8px 32px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05)",
          zIndex: 999, overflow: "hidden",
          animation: "slideUp 0.18s ease",
        }}>
          {/* Header */}
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "10px 12px",
            background: "#0B0F19",
          }}>
            <FileText size={14} color="#94A3B8" style={{ flexShrink: 0 }} />
            <div style={{
              flex: 1, fontSize: 11, color: "white", fontWeight: 600,
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>{file.name}</div>
            <button
              onClick={() => setState("processing")}
              style={{ background: "none", border: "none", cursor: "pointer",
                color: "#94A3B8", padding: 2, fontSize: 14 }}
              title="Expand"
            >↑</button>
            <button
              onClick={onClose}
              style={{ background: "none", border: "none", cursor: "pointer",
                color: "#94A3B8", padding: 2 }}
              title="Dismiss"
            ><X size={12} /></button>
          </div>
          {/* Progress */}
          <div style={{ padding: "10px 12px" }}>
            <div style={{
              display: "flex", justifyContent: "space-between",
              fontSize: 11, color: "#64748B", marginBottom: 6,
            }}>
              <span>{steps.find(s => s.status === "active")?.label || "Processing..."}</span>
              <span style={{ fontWeight: 700, color: "#0066FF" }}>{progress}%</span>
            </div>
            <div style={{
              height: 4, background: "#F1F5F9", borderRadius: 99, overflow: "hidden",
            }}>
              <div style={{
                height: "100%", borderRadius: 99,
                background: "linear-gradient(90deg,#0066FF,#06B6D4)",
                width: `${progress}%`, transition: "width 0.5s ease",
              }} />
            </div>
          </div>
        </div>
      )}

      {/* Minimized complete card */}
      {state === "complete" && result && contractId && (
        <div style={{
          position: "fixed", bottom: 24, right: 24,
          width: 300, background: "white", borderRadius: 14,
          boxShadow: "0 8px 32px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05)",
          zIndex: 999, overflow: "hidden",
          animation: "slideUp 0.18s ease",
        }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "12px 14px",
            background: "#F0FDF4", borderBottom: "1px solid #BBF7D0",
          }}>
            <CheckCircle size={16} color="#16A34A" />
            <div style={{ flex: 1, fontSize: 12, fontWeight: 600, color: "#15803D" }}>
              Analysis Complete!
            </div>
            <button onClick={onClose}
              style={{ background: "none", border: "none", cursor: "pointer", color: "#94A3B8" }}>
              <X size={13} />
            </button>
          </div>
          <div style={{ padding: "10px 14px" }}>
            <div style={{
              fontSize: 11, color: "#64748B", marginBottom: 8,
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>{file?.name}</div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => { onClose(); router.push(`/dashboard/contracts/${contractId}`); }}
                style={{
                  flex: 2, padding: "7px", borderRadius: 8,
                  background: "#0066FF", color: "white", border: "none",
                  fontSize: 11, fontWeight: 700, cursor: "pointer",
                }}
              >View Contract →</button>
              <button
                onClick={() => setState("dropzone")}
                style={{
                  flex: 1, padding: "7px", borderRadius: 8,
                  background: "#F8FAFC", color: "#64748B",
                  border: "1px solid #E2E8F0", fontSize: 11, cursor: "pointer",
                }}
              >Upload More</button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeIn { from { opacity:0 } to { opacity:1 } }
        @keyframes slideUp { from { opacity:0; transform:translate(-50%,-46%) } to { opacity:1; transform:translate(-50%,-50%) } }
        @keyframes spin { to { transform:rotate(360deg) } }
        @keyframes shimmer { 0%{transform:translateX(-100%)} 100%{transform:translateX(100%)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes popIn { from{transform:scale(0.5);opacity:0} to{transform:scale(1);opacity:1} }
      `}</style>
    </>
  );
}
