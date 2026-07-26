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
  flexWrap: "wrap",
  gap: "0.375rem",
};

const chipStyle: React.CSSProperties = {
  padding: "0.25rem 0.75rem",
  background: "#fef3c7",
  color: "#92400e",
  borderRadius: "9999px",
  fontSize: "0.8125rem",
  fontWeight: 500,
};

interface MissingSkillsCardProps {
  skills: string[];
}

export default function MissingSkillsCard({ skills }: MissingSkillsCardProps) {
  if (skills.length === 0) return null;

  return (
    <div style={cardStyle}>
      <p style={titleStyle}>Compétences manquantes</p>
      <ul style={listStyle}>
        {skills.map((skill) => (
          <li key={skill} style={chipStyle}>
            {skill}
          </li>
        ))}
      </ul>
    </div>
  );
}
