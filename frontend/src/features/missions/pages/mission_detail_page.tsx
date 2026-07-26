import { useParams } from "react-router-dom";
import { useMission } from "../hooks/use_mission";
import MissionHeader from "../components/mission_header";
import MissionScoreCard from "../components/mission_score_card";
import DetectedStackCard from "../components/detected_stack_card";
import MatchedSkillsCard from "../components/matched_skills_card";
import MissingSkillsCard from "../components/missing_skills_card";
import MissionSummaryCard from "../components/mission_summary_card";
import MissionExplainabilityCard from "../components/mission_explainability_card";

const pageStyle: React.CSSProperties = {
  maxWidth: "900px",
};

const spinnerContainerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "1rem",
  padding: "4rem 0",
};

const spinnerStyle: React.CSSProperties = {
  width: "2.5rem",
  height: "2.5rem",
  border: "4px solid #e5e7eb",
  borderTopColor: "#4f46e5",
  borderRadius: "50%",
  animation: "spin 0.8s linear infinite",
};

const errorStyle: React.CSSProperties = {
  padding: "0.875rem 1rem",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: "0.375rem",
  color: "#b91c1c",
  fontSize: "0.875rem",
};

const contentStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "1rem",
};

const gridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "1rem",
  alignItems: "start",
};

const leftColStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "1rem",
};

export default function MissionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError, error } = useMission(id ?? "");

  if (isLoading) {
    return (
      <div style={spinnerContainerStyle}>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <div style={spinnerStyle} aria-label="Loading spinner" />
        <p style={{ color: "#6b7280", margin: 0 }}>Chargement de la mission...</p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div style={errorStyle}>
        {error instanceof Error ? error.message : "Mission introuvable"}
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      <div style={contentStyle}>
        <MissionHeader mission={data} />
        <MissionScoreCard mission={data} />

        <div style={gridStyle}>
          <div style={leftColStyle}>
            <DetectedStackCard stack={data.detected_stack} />
            <MatchedSkillsCard skills={data.matched_skills} />
            <MissingSkillsCard skills={data.missing_skills} />
          </div>
          <MissionExplainabilityCard explanation={data.explanation} />
        </div>

        <MissionSummaryCard summary={data.summary} content={data.content} />
      </div>
    </div>
  );
}
