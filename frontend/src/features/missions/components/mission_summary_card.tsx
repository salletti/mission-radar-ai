import { useState } from "react";

const cardStyle: React.CSSProperties = {
  background: "white",
  border: "1px solid #e5e7eb",
  borderRadius: "0.75rem",
  padding: "1.5rem",
  boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
};

const titleStyle: React.CSSProperties = {
  fontSize: "1rem",
  fontWeight: 600,
  color: "#111827",
  margin: "0 0 0.75rem",
};

const summaryStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  color: "#374151",
  lineHeight: 1.6,
  margin: "0 0 1.25rem",
};

const dividerStyle: React.CSSProperties = {
  borderTop: "1px solid #e5e7eb",
  paddingTop: "1.25rem",
  marginTop: "0.5rem",
};

const contentStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  color: "#374151",
  lineHeight: 1.7,
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
};

const toggleStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "#4f46e5",
  fontSize: "0.875rem",
  fontWeight: 500,
  cursor: "pointer",
  padding: "0.5rem 0 0",
};

interface MissionSummaryCardProps {
  summary: string;
  content: string;
}

export default function MissionSummaryCard({ summary, content }: MissionSummaryCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={cardStyle}>
      <p style={titleStyle}>Résumé de l'annonce</p>
      <p style={summaryStyle}>{summary}</p>

      {content && (
        <div style={dividerStyle}>
          <p style={{ ...titleStyle, marginBottom: "0.5rem" }}>Description complète</p>
          {expanded ? (
            <>
              <p style={contentStyle}>{content}</p>
              <button style={toggleStyle} onClick={() => setExpanded(false)}>
                Voir moins ↑
              </button>
            </>
          ) : (
            <>
              <p style={{ ...contentStyle, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 4, WebkitBoxOrient: "vertical" }}>
                {content}
              </p>
              <button style={toggleStyle} onClick={() => setExpanded(true)}>
                Voir plus ↓
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
