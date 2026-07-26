import { useState } from "react";
import SearchQueriesEditor from "./search_queries_editor";

const containerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "1.5rem",
};

const headingStyle: React.CSSProperties = {
  fontSize: "1.5rem",
  fontWeight: 700,
  color: "#111827",
  margin: 0,
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  color: "#6b7280",
  margin: "0.375rem 0 0",
};

const confirmBtnStyle: React.CSSProperties = {
  padding: "0.75rem 2rem",
  background: "#4f46e5",
  color: "white",
  border: "none",
  borderRadius: "0.5rem",
  cursor: "pointer",
  fontSize: "1rem",
  fontWeight: 600,
  alignSelf: "flex-end",
};

const disabledBtnStyle: React.CSSProperties = {
  ...confirmBtnStyle,
  opacity: 0.5,
  cursor: "not-allowed",
};

interface SearchQueriesStepProps {
  initialQueries: string[];
  onConfirm: (queries: string[]) => void;
  isPending: boolean;
}

export default function SearchQueriesStep({
  initialQueries,
  onConfirm,
  isPending,
}: SearchQueriesStepProps) {
  const [queries, setQueries] = useState<string[]>(initialQueries);

  return (
    <div style={containerStyle}>
      <div>
        <h2 style={headingStyle}>Your LinkedIn Search Queries</h2>
        <p style={subtitleStyle}>
          These queries will be used to search for missions on LinkedIn. Edit,
          remove, or add queries before saving.
        </p>
      </div>

      <SearchQueriesEditor value={queries} onChange={setQueries} />

      <button
        type="button"
        style={queries.length === 0 || isPending ? disabledBtnStyle : confirmBtnStyle}
        disabled={queries.length === 0 || isPending}
        onClick={() => onConfirm(queries)}
      >
        {isPending ? "Saving…" : "Save & Go to Dashboard"}
      </button>
    </div>
  );
}
