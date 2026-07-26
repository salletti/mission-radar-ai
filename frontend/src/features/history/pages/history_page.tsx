import { useState } from "react";
import { useHistory, HISTORY_PAGE_LIMIT } from "@/features/history/hooks/use_history";
import HistoryTimeline from "@/features/history/components/history_timeline";

const pageStyle: React.CSSProperties = {
  maxWidth: "760px",
};

const headingStyle: React.CSSProperties = {
  fontSize: "1.5rem",
  fontWeight: 700,
  color: "#111827",
  marginBottom: "0.25rem",
};

const subheadingStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  color: "#6b7280",
  marginBottom: "1.5rem",
};

const spinnerContainerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  padding: "3rem 0",
  color: "#9ca3af",
};

const errorStyle: React.CSSProperties = {
  padding: "1rem",
  background: "#fee2e2",
  borderRadius: "0.5rem",
  color: "#991b1b",
  fontSize: "0.875rem",
};

const emptyStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "3rem 0",
  color: "#9ca3af",
};

const paginationStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginTop: "1.5rem",
  paddingTop: "1rem",
  borderTop: "1px solid #e5e7eb",
};

const pageInfoStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  color: "#6b7280",
};

const btnStyle = (disabled: boolean): React.CSSProperties => ({
  padding: "0.5rem 1rem",
  borderRadius: "0.375rem",
  border: "1px solid #e5e7eb",
  background: disabled ? "#f9fafb" : "white",
  color: disabled ? "#d1d5db" : "#374151",
  fontSize: "0.875rem",
  fontWeight: 500,
  cursor: disabled ? "not-allowed" : "pointer",
});

export default function HistoryPage() {
  const [page, setPage] = useState(0);
  const { data, isLoading, isError } = useHistory(page);

  const totalPages = data ? Math.ceil(data.total / HISTORY_PAGE_LIMIT) : 0;
  const isFirstPage = page === 0;
  const isLastPage = totalPages === 0 || page >= totalPages - 1;

  return (
    <div style={pageStyle}>
      <h1 style={headingStyle}>Historique</h1>
      <p style={subheadingStyle}>Activité récente du produit</p>

      {isLoading && (
        <div style={spinnerContainerStyle}>Chargement…</div>
      )}

      {isError && (
        <div style={errorStyle}>
          Une erreur est survenue lors du chargement de l'historique.
        </div>
      )}

      {!isLoading && !isError && data && data.items.length === 0 && (
        <div style={emptyStyle}>
          <p>Aucune activité pour le moment.</p>
          <p>Les missions matchées apparaîtront ici.</p>
        </div>
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <>
          <HistoryTimeline items={data.items} />

          <div style={paginationStyle}>
            <button
              style={btnStyle(isFirstPage)}
              disabled={isFirstPage}
              onClick={() => setPage((p) => p - 1)}
            >
              ← Précédent
            </button>
            <span style={pageInfoStyle}>
              Page {page + 1} / {totalPages} — {data.total} événement
              {data.total > 1 ? "s" : ""}
            </span>
            <button
              style={btnStyle(isLastPage)}
              disabled={isLastPage}
              onClick={() => setPage((p) => p + 1)}
            >
              Suivant →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
