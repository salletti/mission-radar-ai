const containerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.75rem",
  margin: "1.5rem 0 0.75rem",
};

const lineStyle: React.CSSProperties = {
  flex: 1,
  height: "1px",
  background: "#e5e7eb",
};

const labelStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  fontWeight: 600,
  color: "#9ca3af",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  whiteSpace: "nowrap",
};

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

interface HistoryDateHeaderProps {
  date: string;
}

export default function HistoryDateHeader({ date }: HistoryDateHeaderProps) {
  return (
    <div style={containerStyle}>
      <div style={lineStyle} />
      <span style={labelStyle}>{formatDate(date)}</span>
      <div style={lineStyle} />
    </div>
  );
}
