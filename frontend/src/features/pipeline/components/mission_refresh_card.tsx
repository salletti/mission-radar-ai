import { useMissionRefresh } from "../hooks/use_mission_refresh";
import type { PipelineStep } from "../types/pipeline_run";

const STEPS: { key: PipelineStep; label: string }[] = [
  { key: "collect", label: "Collect" },
  { key: "analyze", label: "Analyze" },
  { key: "match", label: "Match" },
];

const STEP_ORDER: PipelineStep[] = ["collect", "analyze", "match", "done"];

function stepDoneIndex(currentStep: PipelineStep): number {
  return STEP_ORDER.indexOf(currentStep);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: "0.75rem",
  padding: "1.25rem 1.5rem",
  boxShadow: "0 1px 3px rgba(0,0,0,0.07)",
  marginBottom: "1.5rem",
};

const headerStyle: React.CSSProperties = {
  fontSize: "1rem",
  fontWeight: 600,
  color: "#111827",
  margin: "0 0 0.75rem",
};

const syncLabelStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  color: "#6b7280",
  marginBottom: "1rem",
};

const syncValueStyle: React.CSSProperties = {
  fontWeight: 500,
  color: "#374151",
};

const stepsRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "1rem",
  marginBottom: "0.75rem",
};

const progressBarTrackStyle: React.CSSProperties = {
  height: "0.5rem",
  background: "#e5e7eb",
  borderRadius: "999px",
  overflow: "hidden",
  marginBottom: "0.5rem",
};

const progressLabelStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  color: "#6b7280",
  marginBottom: "1rem",
};

const buttonStyle = (disabled: boolean): React.CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  gap: "0.4rem",
  padding: "0.5rem 1rem",
  background: disabled ? "#e5e7eb" : "#4f46e5",
  color: disabled ? "#9ca3af" : "#fff",
  border: "none",
  borderRadius: "0.375rem",
  fontSize: "0.875rem",
  fontWeight: 500,
  cursor: disabled ? "not-allowed" : "pointer",
  transition: "background 0.15s",
});

const errorBoxStyle: React.CSSProperties = {
  padding: "0.75rem 1rem",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: "0.375rem",
  color: "#b91c1c",
  fontSize: "0.875rem",
  marginBottom: "1rem",
};

const successBoxStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
  background: "#d1fae5",
  borderRadius: "0.375rem",
  color: "#065f46",
  fontSize: "0.875rem",
  display: "inline-block",
  marginBottom: "1rem",
};

type StepState = "done" | "active" | "waiting";

function StepIndicator({
  label,
  state,
}: {
  label: string;
  state: StepState;
}) {
  const dotStyle: React.CSSProperties = {
    width: "0.75rem",
    height: "0.75rem",
    borderRadius: "50%",
    display: "inline-block",
    marginRight: "0.375rem",
    background:
      state === "done" ? "#059669" : state === "active" ? "#4f46e5" : "#d1d5db",
    flexShrink: 0,
  };
  const labelColor =
    state === "done" ? "#059669" : state === "active" ? "#4f46e5" : "#9ca3af";

  return (
    <div
      style={{ display: "flex", alignItems: "center", fontSize: "0.8125rem" }}
    >
      <span style={dotStyle} />
      <span style={{ color: labelColor, fontWeight: state === "active" ? 600 : 400 }}>
        {label}
        {state === "done" && " ✓"}
      </span>
    </div>
  );
}

export default function MissionRefreshCard() {
  const {
    pipelineRun,
    lastSyncAt,
    isPolling,
    isTimedOut,
    isStarting,
    startError,
    startRefresh,
  } = useMissionRefresh();

  const isDisabled = isPolling || isStarting;
  const buttonLabel = isStarting
    ? "Démarrage..."
    : isPolling
      ? "En cours..."
      : "Mettre à jour mes missions";

  const doneIdx = pipelineRun ? stepDoneIndex(pipelineRun.current_step) : -1;

  const getStepState = (stepKey: PipelineStep): StepState => {
    const stepIdx = STEP_ORDER.indexOf(stepKey);
    if (doneIdx === -1) return "waiting";
    if (stepIdx < doneIdx) return "done";
    if (stepIdx === doneIdx) return pipelineRun?.status === "completed" ? "done" : "active";
    return "waiting";
  };

  const syncDisplay = () => {
    if (pipelineRun?.status === "completed" && pipelineRun.finished_at) {
      return formatDate(pipelineRun.finished_at);
    }
    if (lastSyncAt) return formatDate(lastSyncAt);
    return "Jamais";
  };

  return (
    <div style={cardStyle}>
      <h2 style={headerStyle}>Synchronisation des missions</h2>

      <p style={syncLabelStyle}>
        Dernière synchronisation :{" "}
        <span style={syncValueStyle}>{syncDisplay()}</span>
      </p>

      {pipelineRun?.status === "completed" && (
        <div style={successBoxStyle}>Pipeline terminé avec succès</div>
      )}

      {(pipelineRun?.status === "failed") && (
        <div style={errorBoxStyle} role="alert">
          Échec du pipeline
          {pipelineRun.error_message ? ` — ${pipelineRun.error_message}` : ""}
        </div>
      )}

      {isTimedOut && (
        <div style={errorBoxStyle} role="alert">
          Pipeline bloqué — veuillez réessayer
        </div>
      )}

      {startError && (
        <div style={errorBoxStyle} role="alert">
          {startError instanceof Error ? startError.message : "Erreur lors du démarrage"}
        </div>
      )}

      {isPolling && pipelineRun && (
        <>
          <div style={stepsRowStyle}>
            {STEPS.map(({ key, label }) => (
              <StepIndicator key={key} label={label} state={getStepState(key)} />
            ))}
          </div>

          <div style={progressBarTrackStyle}>
            <div
              style={{
                height: "100%",
                width: `${Math.round(pipelineRun.progress * 100)}%`,
                background: "#4f46e5",
                borderRadius: "999px",
                transition: "width 0.4s ease",
              }}
            />
          </div>

          <p style={progressLabelStyle}>
            {Math.round(pipelineRun.progress * 100)}%
          </p>
        </>
      )}

      <button
        style={buttonStyle(isDisabled)}
        onClick={startRefresh}
        disabled={isDisabled}
        aria-label="Mettre à jour mes missions"
      >
        {buttonLabel}
      </button>
    </div>
  );
}
