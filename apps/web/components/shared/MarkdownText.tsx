/**
 * Claustor AI — Markdown Text Renderer
 * Renders AI responses with proper formatting.
 * Handles: **bold**, *italic*, bullet lists, numbered lists,
 *          tables, code blocks, headers, line breaks, [N] citations.
 */

import React from "react";

const C = {
  primary: "#5B4BFF",
  heading: "#111827",
  body:    "#374151",
  muted:   "#6B7280",
  border:  "#E5E7EB",
  bg:      "#F9FAFB",
  code:    "#1E293B",
  codeBg:  "#F1F5F9",
};

interface Props {
  content: string;
  color?: string;
}

export function MarkdownText({ content, color = C.body }: Props) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // ── Empty line ──────────────────────────────────
    if (!line.trim()) {
      elements.push(<div key={i} style={{ height: 8 }} />);
      i++;
      continue;
    }

    // ── Code block (```) ───────────────────────────
    if (line.trim().startsWith("```")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      elements.push(
        <pre key={i} style={{
          background: C.codeBg, border: `1px solid ${C.border}`,
          borderRadius: 8, padding: "12px 16px", overflowX: "auto",
          fontSize: 12, fontFamily: "monospace", color: C.code,
          margin: "8px 0", lineHeight: 1.6,
        }}>
          {codeLines.join("\n")}
        </pre>
      );
      continue;
    }

    // ── Table (| col | col |) ──────────────────────
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }

      // Parse table
      const rows = tableLines
        .filter(l => !l.match(/^\s*\|[\s\-:]+\|\s*$/)) // skip separator row
        .map(l =>
          l.trim()
           .replace(/^\|/, "")
           .replace(/\|$/, "")
           .split("|")
           .map(cell => cell.trim())
        );

      if (rows.length > 0) {
        const headers = rows[0];
        const body    = rows.slice(1);
        elements.push(
          <div key={i} style={{ overflowX: "auto", margin: "12px 0" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#F3F4F6" }}>
                  {headers.map((h, hi) => (
                    <th key={hi} style={{
                      padding: "8px 12px", textAlign: "left",
                      fontWeight: 700, color: C.heading,
                      border: `1px solid ${C.border}`,
                      whiteSpace: "nowrap",
                    }}>
                      {renderInline(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, ri) => (
                  <tr key={ri} style={{ background: ri % 2 === 0 ? "#FFFFFF" : "#FAFBFC" }}>
                    {row.map((cell, ci) => (
                      <td key={ci} style={{
                        padding: "8px 12px", color: C.body,
                        border: `1px solid ${C.border}`,
                        verticalAlign: "top",
                      }}>
                        {renderInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // ── Heading # ──────────────────────────────────
    const h3 = line.match(/^###\s+(.+)/);
    const h2 = line.match(/^##\s+(.+)/);
    const h1 = line.match(/^#\s+(.+)/);
    if (h1 || h2 || h3) {
      const text  = (h1 || h2 || h3)![1];
      const size  = h1 ? 18 : h2 ? 16 : 14;
      const weight = h1 ? 800 : 700;
      elements.push(
        <div key={i} style={{ fontSize: size, fontWeight: weight, color: C.heading, margin: "14px 0 6px" }}>
          {renderInline(text)}
        </div>
      );
      i++;
      continue;
    }

    // ── Numbered list ──────────────────────────────
    const numbered = line.match(/^(\d+)\.\s+(.+)/);
    if (numbered) {
      const listItems: Array<[string, string]> = [];
      while (i < lines.length) {
        const m = lines[i].match(/^(\d+)\.\s+(.+)/);
        if (!m) break;
        listItems.push([m[1], m[2]]);
        i++;
      }
      elements.push(
        <div key={i} style={{ margin: "8px 0", display: "flex", flexDirection: "column", gap: 6 }}>
          {listItems.map(([num, text], idx) => (
            <div key={idx} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <span style={{
                minWidth: 22, height: 22, borderRadius: "50%",
                background: C.primary, color: "white",
                fontSize: 11, fontWeight: 700,
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0, marginTop: 1,
              }}>
                {num}
              </span>
              <span style={{ fontSize: 14, color, lineHeight: 1.6 }}>{renderInline(text)}</span>
            </div>
          ))}
        </div>
      );
      continue;
    }

    // ── Bullet list ────────────────────────────────
    const bullet = line.match(/^[-•*]\s+(.+)/);
    if (bullet) {
      const items: string[] = [];
      while (i < lines.length) {
        const m = lines[i].match(/^[-•*]\s+(.+)/);
        if (!m) break;
        items.push(m[1]);
        i++;
      }
      elements.push(
        <div key={i} style={{ margin: "8px 0", display: "flex", flexDirection: "column", gap: 5 }}>
          {items.map((text, idx) => (
            <div key={idx} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <span style={{ color: C.primary, fontWeight: 700, flexShrink: 0, marginTop: 2 }}>•</span>
              <span style={{ fontSize: 14, color, lineHeight: 1.6 }}>{renderInline(text)}</span>
            </div>
          ))}
        </div>
      );
      continue;
    }

    // ── Horizontal rule ────────────────────────────
    if (line.match(/^---+$/)) {
      elements.push(<hr key={i} style={{ border: "none", borderTop: `1px solid ${C.border}`, margin: "12px 0" }} />);
      i++;
      continue;
    }

    // ── Normal paragraph ───────────────────────────
    elements.push(
      <p key={i} style={{ margin: "0 0 6px", fontSize: 14, color, lineHeight: 1.7 }}>
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return <div style={{ color }}>{elements}</div>;
}


// ── Inline renderer ───────────────────────────────────

function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // **bold**
    const bold = remaining.match(/^(.*?)\*\*(.+?)\*\*(.*)/s);
    if (bold) {
      if (bold[1]) parts.push(<span key={key++}>{bold[1]}</span>);
      parts.push(<strong key={key++} style={{ fontWeight: 700, color: C.heading }}>{bold[2]}</strong>);
      remaining = bold[3];
      continue;
    }

    // *italic*
    const italic = remaining.match(/^(.*?)\*(.+?)\*(.*)/s);
    if (italic) {
      if (italic[1]) parts.push(<span key={key++}>{italic[1]}</span>);
      parts.push(<em key={key++} style={{ fontStyle: "italic" }}>{italic[2]}</em>);
      remaining = italic[3];
      continue;
    }

    // `code`
    const code = remaining.match(/^(.*?)`(.+?)`(.*)/s);
    if (code) {
      if (code[1]) parts.push(<span key={key++}>{code[1]}</span>);
      parts.push(
        <code key={key++} style={{
          fontFamily: "monospace", fontSize: "0.88em",
          background: C.codeBg, padding: "1px 6px",
          borderRadius: 4, color: C.primary,
        }}>
          {code[2]}
        </code>
      );
      remaining = code[3];
      continue;
    }

    // [N] or [8.1] citation
    const cite = remaining.match(/^(.*?)(\[\d+(?:\.\d+)?\])(.*)/s);
    if (cite) {
      if (cite[1]) parts.push(<span key={key++}>{cite[1]}</span>);
      parts.push(
        <sup key={key++} style={{
          color: C.primary, fontWeight: 700,
          fontSize: "0.72em", cursor: "default",
          background: "#EEF0FF", padding: "1px 4px",
          borderRadius: 4, marginLeft: 2,
        }}>
          {cite[2]}
        </sup>
      );
      remaining = cite[3];
      continue;
    }

    parts.push(<span key={key++}>{remaining}</span>);
    break;
  }

  return parts;
}
