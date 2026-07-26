import type { Explanation } from "../types/mission_detail";

const cardStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%)",
  border: "1px solid #c4b5fd",
  borderRadius: "0.75rem",
  padding: "1.25rem 1.5rem",
  boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
};

const titleStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  fontWeight: 700,
  color: "#4f46e5",
  margin: "0 0 0.875rem",
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  fontWeight: 600,
  color: "#6d28d9",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  margin: "0.75rem 0 0.375rem",
};

const listStyle: React.CSSProperties = {
  listStyle: "none",
  margin: 0,
  padding: 0,
  display: "flex",
  flexDirection: "column",
  gap: "0.5rem",
};

const itemStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  color: "#374151",
  lineHeight: 1.5,
  display: "flex",
  gap: "0.5rem",
};

const bulletStyle: React.CSSProperties = {
  color: "#7c3aed",
  fontWeight: 700,
  flexShrink: 0,
};

const warningBulletStyle: React.CSSProperties = {
  color: "#d97706",
  fontWeight: 700,
  flexShrink: 0,
};

interface MissionExplainabilityCardProps {
  explanation: Explanation;
}

interface SectionProps {
  items: string[];
  bulletColor?: "violet" | "amber";
}

function ItemList({ items, bulletColor = "violet" }: SectionProps) {
  const bullet = bulletColor === "amber" ? warningBulletStyle : bulletStyle;
  return (
    <ul style={listStyle}>
      {items.map((item, i) => (
        <li key={i} style={itemStyle}>
          <span style={bullet}>•</span>
          {item}
        </li>
      ))}
    </ul>
  );
}

export default function MissionExplainabilityCard({ explanation }: MissionExplainabilityCardProps) {
  const { matching_reasons, strong_points, warnings, recommendations } = explanation;
  const hasContent =
    matching_reasons.length > 0 ||
    strong_points.length > 0 ||
    warnings.length > 0 ||
    recommendations.length > 0;

  if (!hasContent) return null;

  return (
    <div style={cardStyle}>
      <p style={titleStyle}>Pourquoi cette mission vous est proposée</p>

      {matching_reasons.length > 0 && (
        <>
          {(strong_points.length > 0 || warnings.length > 0 || recommendations.length > 0) && (
            <p style={sectionTitleStyle}>Raisons du matching</p>
          )}
          <ItemList items={matching_reasons} />
        </>
      )}

      {strong_points.length > 0 && (
        <>
          <p style={sectionTitleStyle}>Points forts</p>
          <ItemList items={strong_points} />
        </>
      )}

      {warnings.length > 0 && (
        <>
          <p style={sectionTitleStyle}>Points d'attention</p>
          <ItemList items={warnings} bulletColor="amber" />
        </>
      )}

      {recommendations.length > 0 && (
        <>
          <p style={sectionTitleStyle}>Recommandations</p>
          <ItemList items={recommendations} />
        </>
      )}
    </div>
  );
}
