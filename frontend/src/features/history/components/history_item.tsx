import { Link } from "react-router-dom";
import type { ActivityEvent } from "@/features/history/types/activity_event";

const ICONS: Record<string, string> = {
  MISSION_MATCH: "🎯",
};

const itemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  gap: "1rem",
  padding: "0.875rem 1rem",
  background: "white",
  borderRadius: "0.5rem",
  border: "1px solid #e5e7eb",
  marginBottom: "0.5rem",
};

const iconStyle: React.CSSProperties = {
  fontSize: "1.25rem",
  lineHeight: 1,
  flexShrink: 0,
  marginTop: "0.125rem",
};

const bodyStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 0,
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  justifyContent: "space-between",
  gap: "0.5rem",
  marginBottom: "0.25rem",
};

const titleStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  fontWeight: 600,
  color: "#4f46e5",
  textDecoration: "none",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

const plainTitleStyle: React.CSSProperties = {
  ...titleStyle,
  color: "#111827",
};

const metaStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  flexShrink: 0,
};

const timeStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  color: "#9ca3af",
};

const scoreBadgeStyle = (score: number): React.CSSProperties => ({
  display: "inline-block",
  padding: "0.125rem 0.5rem",
  borderRadius: "9999px",
  fontSize: "0.75rem",
  fontWeight: 700,
  background: score >= 70 ? "#d1fae5" : score >= 50 ? "#fef3c7" : "#fee2e2",
  color: score >= 70 ? "#065f46" : score >= 50 ? "#92400e" : "#991b1b",
});

const missionsBadgeStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "0.125rem 0.5rem",
  borderRadius: "9999px",
  fontSize: "0.75rem",
  fontWeight: 700,
  background: "#dbeafe",
  color: "#1e40af",
};

const descriptionStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  color: "#6b7280",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

const errorDescriptionStyle: React.CSSProperties = {
  ...descriptionStyle,
  color: "#991b1b",
};

function getIcon(event: ActivityEvent): string {
  if (event.type === "DAILY_DIGEST") {
    return event.score >= 0 ? "✔" : "❌";
  }
  return ICONS[event.type] ?? "📌";
}

function formatTime(isoDate: string): string {
  return new Date(isoDate).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface HistoryItemProps {
  event: ActivityEvent;
}

export default function HistoryItem({ event }: HistoryItemProps) {
  const isDigest = event.type === "DAILY_DIGEST";
  const isFailed = isDigest && event.score < 0;

  return (
    <div style={itemStyle}>
      <span style={iconStyle}>{getIcon(event)}</span>
      <div style={bodyStyle}>
        <div style={headerRowStyle}>
          {isDigest ? (
            <span style={plainTitleStyle}>{event.title}</span>
          ) : (
            <Link to={`/missions/${event.mission_match_id}`} style={titleStyle}>
              {event.title}
            </Link>
          )}
          <div style={metaStyle}>
            {isDigest ? (
              !isFailed && (
                <span style={missionsBadgeStyle}>{event.score} missions</span>
              )
            ) : (
              <span style={scoreBadgeStyle(event.score)}>{event.score}%</span>
            )}
            <span style={timeStyle}>{formatTime(event.occurred_at)}</span>
          </div>
        </div>
        <p style={isFailed ? errorDescriptionStyle : descriptionStyle}>
          {event.description}
        </p>
      </div>
    </div>
  );
}
