import React from "react";

interface KpiCardProps {
  label: string;
  value: string | number;
  description?: string;
  loading?: boolean;
}

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: "0.5rem",
  padding: "1.25rem 1.5rem",
  display: "flex",
  flexDirection: "column",
  gap: "0.25rem",
};

const labelStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  fontWeight: 500,
  color: "#6b7280",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const valueStyle: React.CSSProperties = {
  fontSize: "1.875rem",
  fontWeight: 700,
  color: "#111827",
  lineHeight: 1.2,
};

const descriptionStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  color: "#9ca3af",
  marginTop: "0.125rem",
};

const skeletonStyle: React.CSSProperties = {
  height: "2rem",
  width: "60%",
  background: "#f3f4f6",
  borderRadius: "0.25rem",
  animation: "pulse 1.5s ease-in-out infinite",
};

export default function KpiCard({ label, value, description, loading }: KpiCardProps) {
  return (
    <div style={cardStyle}>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }`}</style>
      <span style={labelStyle}>{label}</span>
      {loading ? (
        <div style={skeletonStyle} />
      ) : (
        <span style={valueStyle}>{value}</span>
      )}
      {description && !loading && (
        <span style={descriptionStyle}>{description}</span>
      )}
    </div>
  );
}
