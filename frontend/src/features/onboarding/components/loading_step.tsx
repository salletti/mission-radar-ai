const containerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "1.5rem",
  padding: "4rem 2rem",
};

const spinnerStyle: React.CSSProperties = {
  width: "3rem",
  height: "3rem",
  border: "4px solid #e5e7eb",
  borderTopColor: "#4f46e5",
  borderRadius: "50%",
  animation: "spin 0.8s linear infinite",
};

const textStyle: React.CSSProperties = {
  fontSize: "1.125rem",
  color: "#374151",
};

export default function LoadingStep() {
  return (
    <div style={containerStyle}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <div style={spinnerStyle} aria-label="Loading spinner" />
      <p style={textStyle}>Analyzing your CV...</p>
    </div>
  );
}
