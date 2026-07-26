import type { MissionDetail } from "../types/mission_detail";

interface MissionScoreCardProps {
  mission: MissionDetail;
}

const cardStyle: React.CSSProperties = {
  background: "white",
  border: "1px solid #e5e7eb",
  borderRadius: "0.75rem",
  padding: "1.5rem",
  boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "1.25rem",
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: "1rem",
  fontWeight: 600,
  color: "#111827",
  margin: 0,
};

const scoreDisplayStyle: React.CSSProperties = {
  fontSize: "2rem",
  fontWeight: 800,
  color: "#4f46e5",
};

const subScoresGridStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.75rem",
};

const subScoreRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.75rem",
};

const subScoreLabelStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  color: "#6b7280",
  width: "9rem",
  flexShrink: 0,
};

const barContainerStyle: React.CSSProperties = {
  flex: 1,
  height: "6px",
  background: "#e5e7eb",
  borderRadius: "9999px",
  overflow: "hidden",
};

const subScoreValueStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  fontWeight: 600,
  color: "#374151",
  width: "2.5rem",
  textAlign: "right",
};

function barFill(score: number): string {
  if (score >= 0.8) return "#10b981";
  if (score >= 0.5) return "#f59e0b";
  return "#ef4444";
}

const _SUB_SCORES = [
  { key: "semantic", label: "Correspondance sémantique", weight: "70%" },
  { key: "contract", label: "Type de contrat", weight: "15%" },
  { key: "remote", label: "Télétravail", weight: "10%" },
  { key: "tjm", label: "TJM", weight: "5%" },
] as const;

export default function MissionScoreCard({ mission }: MissionScoreCardProps) {
  const globalPercent = Math.round(mission.global_score * 100);

  return (
    <div style={cardStyle}>
      <div style={headerRowStyle}>
        <p style={sectionTitleStyle}>Score de matching</p>
        <span style={scoreDisplayStyle}>{globalPercent}%</span>
      </div>

      <div style={subScoresGridStyle}>
        {_SUB_SCORES.map(({ key, label, weight }) => {
          const score = mission.score_details[key as keyof typeof mission.score_details];
          const percent = Math.round(score * 100);
          return (
            <div key={key} style={subScoreRowStyle}>
              <span style={subScoreLabelStyle}>
                {label}
                <span style={{ color: "#9ca3af", marginLeft: "0.25rem" }}>
                  ({weight})
                </span>
              </span>
              <div style={barContainerStyle}>
                <div
                  style={{
                    height: "100%",
                    width: `${percent}%`,
                    background: barFill(score),
                    borderRadius: "9999px",
                  }}
                />
              </div>
              <span style={subScoreValueStyle}>{percent}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
