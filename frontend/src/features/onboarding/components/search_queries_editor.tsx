import { useState, type KeyboardEvent } from "react";

const chipsStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.5rem",
  marginBottom: "1rem",
};

const chipRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  padding: "0.5rem 0.75rem",
  background: "#eff6ff",
  border: "1px solid #bfdbfe",
  borderRadius: "0.5rem",
  fontSize: "0.9375rem",
};

const chipTextStyle: React.CSSProperties = {
  flex: 1,
  color: "#1e40af",
  fontWeight: 500,
};

const chipInputStyle: React.CSSProperties = {
  flex: 1,
  padding: "0.125rem 0.25rem",
  border: "1px solid #3b82f6",
  borderRadius: "0.25rem",
  fontSize: "0.9375rem",
  color: "#1e40af",
  outline: "none",
  background: "white",
};

const iconBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  cursor: "pointer",
  padding: "0.125rem 0.25rem",
  lineHeight: 1,
  display: "flex",
  alignItems: "center",
  borderRadius: "0.25rem",
};

const inputRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.5rem",
};

const newInputStyle: React.CSSProperties = {
  flex: 1,
  padding: "0.5rem 0.75rem",
  border: "1px solid #d1d5db",
  borderRadius: "0.375rem",
  fontSize: "0.875rem",
  outline: "none",
};

const addBtnStyle: React.CSSProperties = {
  padding: "0.5rem 1rem",
  background: "#4f46e5",
  color: "white",
  border: "none",
  borderRadius: "0.375rem",
  cursor: "pointer",
  fontSize: "0.875rem",
  fontWeight: 500,
};

interface SearchQueriesEditorProps {
  value: string[];
  onChange: (queries: string[]) => void;
}

export default function SearchQueriesEditor({
  value,
  onChange,
}: SearchQueriesEditorProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState("");
  const [newQuery, setNewQuery] = useState("");

  const startEdit = (index: number) => {
    setEditingIndex(index);
    setEditingValue(value[index]);
  };

  const commitEdit = () => {
    if (editingIndex === null) return;
    const trimmed = editingValue.trim();
    if (trimmed && !value.some((q, i) => q === trimmed && i !== editingIndex)) {
      const updated = [...value];
      updated[editingIndex] = trimmed;
      onChange(updated);
    }
    setEditingIndex(null);
    setEditingValue("");
  };

  const cancelEdit = () => {
    setEditingIndex(null);
    setEditingValue("");
  };

  const handleEditKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitEdit();
    }
    if (e.key === "Escape") {
      cancelEdit();
    }
  };

  const removeQuery = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const addQuery = () => {
    const trimmed = newQuery.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
    }
    setNewQuery("");
  };

  const handleNewKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addQuery();
    }
  };

  return (
    <div>
      <div style={chipsStyle}>
        {value.map((query, index) => (
          <div key={index} style={chipRowStyle}>
            {editingIndex === index ? (
              <>
                <input
                  style={chipInputStyle}
                  value={editingValue}
                  autoFocus
                  onChange={(e) => setEditingValue(e.target.value)}
                  onKeyDown={handleEditKeyDown}
                  onBlur={commitEdit}
                  aria-label={`Edit query ${index + 1}`}
                />
                <button
                  type="button"
                  style={{ ...iconBtnStyle, color: "#16a34a" }}
                  onClick={commitEdit}
                  aria-label="Confirm edit"
                >
                  ✓
                </button>
                <button
                  type="button"
                  style={{ ...iconBtnStyle, color: "#6b7280" }}
                  onClick={cancelEdit}
                  aria-label="Cancel edit"
                >
                  ✕
                </button>
              </>
            ) : (
              <>
                <span style={chipTextStyle}>{query}</span>
                <button
                  type="button"
                  style={{ ...iconBtnStyle, color: "#2563eb" }}
                  onClick={() => startEdit(index)}
                  aria-label={`Edit "${query}"`}
                >
                  ✎
                </button>
                <button
                  type="button"
                  style={{ ...iconBtnStyle, color: "#dc2626" }}
                  onClick={() => removeQuery(index)}
                  aria-label={`Remove "${query}"`}
                >
                  ×
                </button>
              </>
            )}
          </div>
        ))}
      </div>

      <div style={inputRowStyle}>
        <input
          style={newInputStyle}
          value={newQuery}
          onChange={(e) => setNewQuery(e.target.value)}
          onKeyDown={handleNewKeyDown}
          placeholder="Add a search query and press Enter..."
          aria-label="New search query"
        />
        <button type="button" style={addBtnStyle} onClick={addQuery}>
          Add
        </button>
      </div>
    </div>
  );
}
