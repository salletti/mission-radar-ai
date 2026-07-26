import React from "react";
import KpiCard from "./kpi_card";
import { useDashboardSummary } from "../hooks/use_dashboard_summary";

const PIPELINE_STATUS_LABELS: Record<string, string> = {
  completed: "Terminé",
  running: "En cours",
  pending: "En attente",
  failed: "Échec",
  cancelled: "Annulé",
};

const PIPELINE_STATUS_COLORS: Record<string, string> = {
  completed: "#16a34a",
  running: "#2563eb",
  pending: "#d97706",
  failed: "#dc2626",
  cancelled: "#6b7280",
};

const HEALTH_COLORS: Record<string, string> = {
  OK: "#16a34a",
  DEGRADED: "#dc2626",
  UNKNOWN: "#9ca3af",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "1.5rem",
};

const gridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "1rem",
  marginBottom: "1rem",
};

const rowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "1rem",
};

const metaCardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: "0.5rem",
  padding: "1rem 1.5rem",
  display: "flex",
  alignItems: "center",
  gap: "0.75rem",
};

const metaLabelStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  fontWeight: 500,
  color: "#6b7280",
  textTransform: "uppercase" as const,
  letterSpacing: "0.05em",
};

const metaValueStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  fontWeight: 600,
  color: "#111827",
};

const dotStyle = (color: string): React.CSSProperties => ({
  width: "0.625rem",
  height: "0.625rem",
  borderRadius: "50%",
  background: color,
  flexShrink: 0,
});

const errorStyle: React.CSSProperties = {
  padding: "0.75rem 1rem",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: "0.375rem",
  color: "#b91c1c",
  fontSize: "0.875rem",
  marginBottom: "1rem",
};

function formatLastRefresh(iso: string | null): string {
  if (!iso) return "Jamais";
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardSummarySection() {
  const { data, isLoading, isError } = useDashboardSummary();

  if (isError) {
    return (
      <div style={sectionStyle}>
        <div style={errorStyle}>Impossible de charger le résumé du tableau de bord.</div>
      </div>
    );
  }

  const pipelineStatus = data?.kpis.pipeline_status ?? null;
  const healthStatus = data?.health.status ?? "UNKNOWN";
  const duration = data?.health.last_pipeline_duration_seconds;

  const healthColor = HEALTH_COLORS[healthStatus] ?? "#9ca3af";
  const statusColor = pipelineStatus ? (PIPELINE_STATUS_COLORS[pipelineStatus] ?? "#6b7280") : "#9ca3af";
  const statusLabel = pipelineStatus ? (PIPELINE_STATUS_LABELS[pipelineStatus] ?? pipelineStatus) : "—";

  return (
    <div style={sectionStyle}>
      <div style={gridStyle}>
        <KpiCard
          label="Missions totales"
          value={isLoading ? "" : (data?.kpis.total_missions ?? 0)}
          loading={isLoading}
        />
        <KpiCard
          label="Nouvelles aujourd'hui"
          value={isLoading ? "" : (data?.kpis.new_today ?? 0)}
          loading={isLoading}
        />
        <KpiCard
          label="Score moyen"
          value={isLoading ? "" : `${data?.kpis.average_score ?? 0}%`}
          loading={isLoading}
        />
        <KpiCard
          label="Dernière sync"
          value={isLoading ? "" : formatLastRefresh(data?.kpis.last_refresh ?? null)}
          loading={isLoading}
        />
      </div>

      <div style={rowStyle}>
        <div style={metaCardStyle}>
          <div style={dotStyle(statusColor)} />
          <div>
            <div style={metaLabelStyle}>Statut pipeline</div>
            <div style={{ ...metaValueStyle, color: statusColor }}>{isLoading ? "—" : statusLabel}</div>
          </div>
        </div>

        <div style={metaCardStyle}>
          <div style={dotStyle(healthColor)} />
          <div>
            <div style={metaLabelStyle}>Santé système</div>
            <div style={{ ...metaValueStyle, color: healthColor }}>
              {isLoading ? "—" : healthStatus}
            </div>
            {!isLoading && duration !== null && duration !== undefined && (
              <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.125rem" }}>
                Durée : {Math.round(duration)}s
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
