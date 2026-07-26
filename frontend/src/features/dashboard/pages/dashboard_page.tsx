import { useTodayMissions } from "../hooks/use_today_missions";
import MissionCard from "../components/mission_card";
import MissionRefreshCard from "@/features/pipeline/components/mission_refresh_card";
import DashboardSummarySection from "@/features/summary/components/dashboard_summary_section";

const pageStyle: React.CSSProperties = {
  maxWidth: "900px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "1.5rem",
  fontWeight: 700,
  color: "#111827",
  margin: "0 0 1.5rem",
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

const emptyStyle: React.CSSProperties = {
  padding: "3rem 0",
  textAlign: "center",
  color: "#6b7280",
  fontSize: "0.9375rem",
};

const listStyle: React.CSSProperties = {
  listStyle: "none",
  padding: 0,
  margin: 0,
  display: "flex",
  flexDirection: "column",
  gap: "1rem",
};

export default function DashboardPage() {
  const { data, isLoading, isError, error } = useTodayMissions();

  return (
    <div style={pageStyle}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <MissionRefreshCard />
      <DashboardSummarySection />
      <h1 style={titleStyle}>Missions du jour</h1>

      {isLoading && (
        <div style={spinnerContainerStyle}>
          <div style={spinnerStyle} aria-label="Loading spinner" />
          <p style={{ color: "#6b7280", margin: 0 }}>Chargement des missions...</p>
        </div>
      )}

      {isError && (
        <div style={errorStyle}>
          {error instanceof Error ? error.message : "Une erreur est survenue"}
        </div>
      )}

      {!isLoading && !isError && data?.length === 0 && (
        <p style={emptyStyle}>
          Aucune mission aujourd'hui. Le scraping tourne automatiquement chaque matin.
        </p>
      )}

      {data && data.length > 0 && (
        <ul style={listStyle}>
          {data.map((mission) => (
            <MissionCard key={mission.mission_match_id} mission={mission} />
          ))}
        </ul>
      )}
    </div>
  );
}
