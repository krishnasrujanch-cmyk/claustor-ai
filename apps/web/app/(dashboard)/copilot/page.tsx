"use client";

import { useEffect, useRef, useState } from "react";
import { chat as chatAPI, contracts as contractsAPI, Contract } from "@/lib/api";
import { MarkdownText } from "@/components/shared/MarkdownText";

const C = {
  primary:"#5B4BFF", primaryLight:"#EEF0FF", accent:"#06B6D4",
  heading:"#111827", body:"#374151", muted:"#6B7280",
  border:"#E5E7EB", surface:"#FFFFFF", bg:"#FAFBFC",
};

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Array<{
    citation_number: number;
    clause_type: string;
    source: string;
    text_preview: string;
    rrf_score: number;
  }>;
  isLoading?: boolean;
}

const SUGGESTED_QUESTIONS = [
  "What is the liability cap?",
  "Who are the parties to this contract?",
  "What are the payment terms?",
  "Is there an auto-renewal clause?",
  "What is the governing law?",
  "What are the termination conditions?",
];

export default function CopilotPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    contractsAPI.list({ status:"analyzed", page_size:50 })
      .then(d => setContracts(d.contracts));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior:"smooth" });
  }, [messages]);

  const sendMessage = async (query: string) => {
    if (!query.trim() || isLoading) return;
    setMessages(prev => [...prev,
      { role:"user", content:query },
      { role:"assistant", content:"", isLoading:true },
    ]);
    setInput("");
    setIsLoading(true);
    try {
      const r = await chatAPI.send(query, selectedContract||undefined);
      setMessages(prev => [...prev.slice(0,-1), {
        role:"assistant", content:r.answer, citations:r.citations,
      }]);
    } catch {
      setMessages(prev => [...prev.slice(0,-1), {
        role:"assistant", content:"Sorry, I couldn't process that query. Please try again.",
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ height:"100%", display:"flex", flexDirection:"column", maxWidth:900, margin:"0 auto", padding:"0 24px" }}>
      {/* Header */}
      <div style={{ padding:"24px 0 16px", borderBottom:`1px solid ${C.border}`, display:"flex", justifyContent:"space-between", alignItems:"center", flexShrink:0 }}>
        <div>
          <h1 style={{ fontSize:20, fontWeight:800, color:C.heading, marginBottom:2 }}>AI Copilot</h1>
          <p style={{ fontSize:13, color:C.muted }}>Ask anything about your contracts. Answers cited from the actual document.</p>
        </div>
        <select value={selectedContract} onChange={e=>{ setSelectedContract(e.target.value); setMessages([]); }}
          style={{ padding:"8px 12px", border:`1.5px solid ${C.border}`, borderRadius:8, fontSize:13, color:C.body, background:C.surface, minWidth:200 }}>
          <option value="">All contracts</option>
          {contracts.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
      </div>

      {/* Messages */}
      <div style={{ flex:1, overflowY:"auto", padding:"24px 0", display:"flex", flexDirection:"column", gap:20 }}>
        {messages.length === 0 && (
          <div style={{ textAlign:"center", paddingTop:60 }}>
            <div style={{ fontSize:48, marginBottom:16 }}>🤖</div>
            <h2 style={{ fontSize:18, fontWeight:700, color:C.heading, marginBottom:8 }}>Ask your contracts anything</h2>
            <p style={{ fontSize:14, color:C.muted, marginBottom:32 }}>
              {selectedContract ? "Ask about the selected contract" : "Select a contract or ask across all"}
            </p>
            <div style={{ display:"flex", flexWrap:"wrap", gap:8, justifyContent:"center", maxWidth:600, margin:"0 auto" }}>
              {SUGGESTED_QUESTIONS.map(q=>(
                <button key={q} onClick={()=>sendMessage(q)}
                  style={{ padding:"8px 14px", border:`1.5px solid ${C.border}`, borderRadius:20, background:C.surface, color:C.body, fontSize:13, cursor:"pointer" }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{ display:"flex", justifyContent:msg.role==="user"?"flex-end":"flex-start", gap:12 }}>
            {msg.role === "assistant" && (
              <div style={{ width:32, height:32, borderRadius:"50%", background:C.primary, display:"flex", alignItems:"center", justifyContent:"center", color:"white", fontSize:14, flexShrink:0, marginTop:4 }}>
                🤖
              </div>
            )}
            <div style={{ maxWidth:"75%" }}>
              <div style={{
                padding:"12px 16px",
                borderRadius: msg.role==="user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                background: msg.role==="user" ? C.primary : C.surface,
                color: msg.role==="user" ? "white" : C.body,
                border: msg.role==="assistant" ? `1px solid ${C.border}` : "none",
              }}>
                {msg.isLoading ? (
                  <div style={{ display:"flex", gap:4, padding:"4px 0" }}>
                    {[0,1,2].map(i=>(
                      <div key={i} style={{ width:8, height:8, borderRadius:"50%", background:C.muted, animation:`bounce 1s ease-in-out ${i*0.15}s infinite` }}/>
                    ))}
                  </div>
                ) : msg.role === "assistant" ? (
                  <MarkdownText content={msg.content} color={C.body} />
                ) : (
                  <span style={{ fontSize:14 }}>{msg.content}</span>
                )}
              </div>

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div style={{ marginTop:8, display:"flex", flexDirection:"column", gap:4 }}>
                  {msg.citations.slice(0,3).map(cite=>(
                    <div key={cite.citation_number} style={{ display:"flex", gap:8, padding:"6px 10px", background:C.bg, border:`1px solid ${C.border}`, borderRadius:8, fontSize:12 }}>
                      <span style={{ width:18, height:18, borderRadius:"50%", background:C.primaryLight, color:C.primary, display:"flex", alignItems:"center", justifyContent:"center", fontWeight:700, flexShrink:0, fontSize:10 }}>
                        {cite.citation_number}
                      </span>
                      <div>
                        <span style={{ fontSize:10, fontWeight:600, color:C.primary, textTransform:"uppercase", letterSpacing:"0.05em" }}>
                          {cite.clause_type || cite.source}
                        </span>
                        <p style={{ color:C.muted, margin:0, lineHeight:1.4, marginTop:2 }}>
                          {cite.text_preview.slice(0,80)}...
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{ padding:"16px 0 24px", borderTop:`1px solid ${C.border}`, flexShrink:0 }}>
        <form onSubmit={e=>{e.preventDefault();sendMessage(input);}} style={{ display:"flex", gap:10 }}>
          <input value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask anything about your contracts..."
            disabled={isLoading}
            style={{ flex:1, padding:"12px 16px", border:`1.5px solid ${C.border}`, borderRadius:10, fontSize:14, color:C.body, background:C.surface, outline:"none" }}
            onFocus={e=>e.target.style.borderColor=C.primary}
            onBlur={e=>e.target.style.borderColor=C.border}
          />
          <button type="submit" disabled={isLoading||!input.trim()}
            style={{ padding:"12px 20px", background:isLoading||!input.trim()?"#D1D5DB":C.primary, color:"white", border:"none", borderRadius:10, fontSize:14, fontWeight:600, cursor:isLoading||!input.trim()?"not-allowed":"pointer" }}>
            {isLoading ? "..." : "Ask →"}
          </button>
        </form>
        <p style={{ fontSize:11, color:C.muted, marginTop:8 }}>Answers cited from your contracts. Not legal advice.</p>
      </div>

      <style>{`@keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}`}</style>
    </div>
  );
}
