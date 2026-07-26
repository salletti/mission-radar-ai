import { Link } from "react-router-dom";
import type { MissionDetail } from "../types/mission_detail";

interface MissionHeaderProps {
  mission: MissionDetail;
}

const _CONTRACT_LABELS: Record<string, string> = {
  freelance: "Freelance",
  permanent: "CDI",
  fixed_term: "CDD",
  internship: "Stage",
  apprenticeship: "Alternance",
  unknown: "Non spécifié",
};

const _REMOTE_LABELS: Record<string, string> = {
  full_remote: "Full Remote",
  hybrid: "Hybride",
  onsite: "Présentiel",
  unknown: "Non spécifié",
};

const cardStyle: React.CSSProperties = {
  background: "white",
  border: "1px solid #e5e7eb",
  borderRadius: "0.75rem",
  padding: "1.5rem",
  boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
};

const backLinkStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "0.375rem",
  color: "#6b7280",
  fontSize: "0.875rem",
  textDecoration: "none",
  marginBottom: "1.25rem",
};

const titleStyle: React.CSSProperties = {
  fontSize: "1.375rem",
  fontWeight: 700,
  color: "#111827",
  margin: "0 0 0.375rem",
};

const companyRowStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  color: "#374151",
  marginBottom: "0.875rem",
};

const badgesRowStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "0.5rem",
  marginBottom: "1rem",
};

const badgeStyle = (color: string, bg: string): React.CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  padding: "0.25rem 0.75rem",
  borderRadius: "9999px",
  fontSize: "0.8125rem",
  fontWeight: 500,
  background: bg,
  color: color,
});

const postLinkStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  color: "#4f46e5",
  textDecoration: "none",
  fontWeight: 500,
};

export default function MissionHeader({ mission }: MissionHeaderProps) {
  const contractLabel =
    _CONTRACT_LABELS[mission.detected_contract_type] ?? mission.detected_contract_type;
  const remoteLabel =
    _REMOTE_LABELS[mission.detected_remote_mode] ?? mission.detected_remote_mode;

  return (
    <>
      <Link to="/dashboard" style={backLinkStyle}>
        ← Retour au Dashboard
      </Link>

      <div style={cardStyle}>
        <h1 style={titleStyle}>
          {mission.title ?? "Mission sans titre"}
        </h1>

        <div style={companyRowStyle}>
          {[mission.company, mission.location].filter(Boolean).join(" · ")}
        </div>

        <div style={badgesRowStyle}>
          <span style={badgeStyle("#4f46e5", "#ede9fe")}>{contractLabel}</span>
          <span style={badgeStyle("#0369a1", "#e0f2fe")}>{remoteLabel}</span>
          {mission.detected_tjm && (
            <span style={badgeStyle("#065f46", "#d1fae5")}>
              {mission.detected_tjm.toFixed(0)}€/j
            </span>
          )}
          {mission.seniority && (
            <span style={badgeStyle("#92400e", "#fef3c7")}>{mission.seniority}</span>
          )}
        </div>

        {mission.post_url && (
          <a
            href={mission.post_url}
            target="_blank"
            rel="noopener noreferrer"
            style={postLinkStyle}
          >
            Voir l'annonce originale →
          </a>
        )}
      </div>
    </>
  );
}
