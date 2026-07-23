/**
 * Claustor AI — Markdown Text Renderer
 * Renders AI responses with proper formatting.
 * Handles: **bold**, bullet lists, numbered lists, line breaks.
 * No external dependencies.
 */

interface MarkdownTextProps {
  content: string;
  color?: string;
}

export function MarkdownText({ content, color = "#374151" }: MarkdownTextProps) {
  const lines = content.split("\n");

  const renderLine = (line: string, idx: number) => {
    // Empty line
    if (!line.trim()) return <br key={idx} />;

    // Numbered list: "1. item"
    const numbered = line.match(/^(\d+)\.\s+(.+)/);
    if (numbered) {
      return (
        <div key={idx} style={{ display: "flex", gap: 10, marginBottom: 6 }}>
          <span style={{ minWidth: 20, fontWeight: 700, color: "#5B4BFF" }}>
            {numbered[1]}.
          </span>
          <span>{renderInline(numbered[2])}</span>
        </div>
      );
    }

    // Bullet list: "- item" or "• item"
    const bullet = line.match(/^[-•*]\s+(.+)/);
    if (bullet) {
      return (
        <div key={idx} style={{ display: "flex", gap: 10, marginBottom: 6 }}>
          <span style={{ minWidth: 16, color: "#5B4BFF", fontWeight: 700 }}>•</span>
          <span>{renderInline(bullet[1])}</span>
        </div>
      );
    }

    // Normal line
    return (
      <p key={idx} style={{ margin: "0 0 6px", lineHeight: 1.7 }}>
        {renderInline(line)}
      </p>
    );
  };

  // Render inline: **bold**, *italic*, `code`, [N] citations
  const renderInline = (text: string) => {
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let keyIdx = 0;

    while (remaining.length > 0) {
      // **bold**
      const bold = remaining.match(/^(.*?)\*\*(.+?)\*\*(.*)/s);
      if (bold) {
        if (bold[1]) parts.push(<span key={keyIdx++}>{bold[1]}</span>);
        parts.push(<strong key={keyIdx++} style={{ fontWeight: 700, color: "#111827" }}>{bold[2]}</strong>);
        remaining = bold[3];
        continue;
      }

      // `code`
      const code = remaining.match(/^(.*?)`(.+?)`(.*)/s);
      if (code) {
        if (code[1]) parts.push(<span key={keyIdx++}>{code[1]}</span>);
        parts.push(
          <code key={keyIdx++} style={{ fontFamily: "monospace", fontSize: "0.9em", background: "#F3F4F6", padding: "1px 6px", borderRadius: 4, color: "#5B4BFF" }}>
            {code[2]}
          </code>
        );
        remaining = code[3];
        continue;
      }

      // [N] citation reference
      const cite = remaining.match(/^(.*?)(\[\d+(?:\.\d+)?\])(.*)/s);
      if (cite) {
        if (cite[1]) parts.push(<span key={keyIdx++}>{cite[1]}</span>);
        parts.push(
          <sup key={keyIdx++} style={{ color: "#5B4BFF", fontWeight: 700, fontSize: "0.75em", cursor: "default" }} title="Citation">
            {cite[2]}
          </sup>
        );
        remaining = cite[3];
        continue;
      }

      // No more patterns
      parts.push(<span key={keyIdx++}>{remaining}</span>);
      break;
    }

    return parts;
  };

  return (
    <div style={{ color, fontSize: 14, lineHeight: 1.7 }}>
      {lines.map((line, idx) => renderLine(line, idx))}
    </div>
  );
}
