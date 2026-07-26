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

const listStyle: React.CSSProperties = {
  listStyle: "none",
  margin: 0,
  padding: 0,
  display: "flex",
  flexDirection: "column",
  gap: "0.375rem",
};

const itemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  fontSize: "0.875rem",
  color: "#374151",
};

const checkStyle: React.CSSProperties = {
  color: "#10b981",
  fontWeight: 700,
  fontSize: "0.9375rem",
};

interface MatchedSkillsCardProps {
  skills: string[];
}

export default function MatchedSkillsCard({ skills }: MatchedSkillsCardProps) {
  if (skills.length === 0) return null;

  return (
    <div style={cardStyle}>
      <p style={titleStyle}>Compétences matchées</p>
      <ul style={listStyle}>
        {skills.map((skill) => (
          <li key={skill} style={itemStyle}>
            <span style={checkStyle}>✓</span>
            {skill}
          </li>
        ))}
      </ul>
    </div>
  );
}
