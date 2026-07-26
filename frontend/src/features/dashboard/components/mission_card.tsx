import { Link } from "react-router-dom";
import type { TodayMission } from "../types/mission";

interface MissionCardProps {
  mission: TodayMission;
}

const cardStyle: React.CSSProperties = {
  background: "white",
  border: "1px solid #e5e7eb",
  borderRadius: "0.75rem",
  padding: "1.25rem 1.5rem",
  display: "flex",
  flexDirection: "column",
  gap: "0.875rem",
  boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const authorStyle: React.CSSProperties = {
  fontWeight: 700,
  fontSize: "0.9375rem",
  color: "#111827",
  margin: 0,
};

const scoreTextStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  fontWeight: 700,
  color: "#4f46e5",
};

const scoreBarContainerStyle: React.CSSProperties = {
  height: "6px",
  background: "#e5e7eb",
  borderRadius: "9999px",
  overflow: "hidden",
};

const excerptStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  color: "#374151",
  margin: 0,
  overflow: "hidden",
  display: "-webkit-box",
  WebkitLineClamp: 3,
  WebkitBoxOrient: "vertical",
  lineHeight: 1.5,
};

const stackRowStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "0.375rem",
};

const chipStyle: React.CSSProperties = {
  padding: "0.1875rem 0.625rem",
  background: "#ede9fe",
  color: "#4f46e5",
  borderRadius: "9999px",
  fontSize: "0.8125rem",
  fontWeight: 500,
};

const metaRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const metaTextStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  color: "#6b7280",
};

const linkStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  color: "#4f46e5",
  fontWeight: 500,
  textDecoration: "none",
};

export default function MissionCard({ mission }: MissionCardProps) {
  const scorePercent = Math.round(mission.global_score * 100);

  return (
    <li style={cardStyle}>
      <div style={headerRowStyle}>
        <p style={authorStyle}>{mission.author_name}</p>
        <span style={scoreTextStyle}>{scorePercent}%</span>
      </div>

      <div style={scoreBarContainerStyle}>
        <div
          style={{
            height: "100%",
            width: `${scorePercent}%`,
            background: "#4f46e5",
            borderRadius: "9999px",
          }}
        />
      </div>

      <p style={excerptStyle}>{mission.content_excerpt}</p>

      {mission.detected_stack.length > 0 && (
        <div style={stackRowStyle}>
          {mission.detected_stack.map((tech) => (
            <span key={tech} style={chipStyle}>
              {tech}
            </span>
          ))}
        </div>
      )}

      <div style={metaRowStyle}>
        <span style={metaTextStyle}>
          {mission.detected_contract_type} · {mission.detected_remote_mode}
        </span>
        <Link to={`/missions/${mission.mission_match_id}`} style={linkStyle}>
          Voir le détail
        </Link>
      </div>
    </li>
  );
}
