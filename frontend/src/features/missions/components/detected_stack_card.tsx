const cardStyle: React.CSSProperties = {
  background: "white",
  border: "1px solid #e5e7eb",
  borderRadius: "0.75rem",
  padding: "1.25rem 1.5rem",
  boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
};

const titleStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  fontWeight: 600,
  color: "#111827",
  margin: "0 0 0.875rem",
};

const chipsRowStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "0.375rem",
};

const chipStyle: React.CSSProperties = {
  padding: "0.25rem 0.75rem",
  background: "#ede9fe",
  color: "#4f46e5",
  borderRadius: "9999px",
  fontSize: "0.8125rem",
  fontWeight: 500,
};

interface DetectedStackCardProps {
  stack: string[];
}

export default function DetectedStackCard({ stack }: DetectedStackCardProps) {
  if (stack.length === 0) return null;

  return (
    <div style={cardStyle}>
      <p style={titleStyle}>Stack détectée</p>
      <div style={chipsRowStyle}>
        {stack.map((tech) => (
          <span key={tech} style={chipStyle}>
            {tech}
          </span>
        ))}
      </div>
    </div>
  );
}
