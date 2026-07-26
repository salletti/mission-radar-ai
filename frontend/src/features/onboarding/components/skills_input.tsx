import { useState, type KeyboardEvent } from "react";

const chipsStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "0.5rem",
  marginBottom: "0.5rem",
  minHeight: "2rem",
};

const chipStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "0.375rem",
  padding: "0.25rem 0.625rem",
  background: "#ede9fe",
  color: "#4f46e5",
  borderRadius: "9999px",
  fontSize: "0.875rem",
  fontWeight: 500,
};

const removeBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  cursor: "pointer",
  color: "#7c3aed",
  fontSize: "1rem",
  lineHeight: 1,
  padding: 0,
  display: "flex",
  alignItems: "center",
};

const inputRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.5rem",
};

const inputStyle: React.CSSProperties = {
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

const errorStyle: React.CSSProperties = {
  color: "#ef4444",
  fontSize: "0.875rem",
  margin: "0.25rem 0 0",
};

interface SkillsInputProps {
  value: string[];
  onChange: (skills: string[]) => void;
  error?: string;
}

export default function SkillsInput({ value, onChange, error }: SkillsInputProps) {
  const [inputValue, setInputValue] = useState("");

  const addSkill = () => {
    const skill = inputValue.trim();
    if (skill && !value.includes(skill)) {
      onChange([...value, skill]);
    }
    setInputValue("");
  };

  const removeSkill = (skill: string) => {
    onChange(value.filter((s) => s !== skill));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addSkill();
    }
  };

  return (
    <div>
      <div style={chipsStyle}>
        {value.map((skill) => (
          <span key={skill} style={chipStyle}>
            {skill}
            <button
              type="button"
              style={removeBtnStyle}
              onClick={() => removeSkill(skill)}
              aria-label={`Remove ${skill}`}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div style={inputRowStyle}>
        <input
          style={inputStyle}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add a skill and press Enter..."
          aria-label="New skill"
        />
        <button type="button" style={addBtnStyle} onClick={addSkill}>
          Add
        </button>
      </div>
      {error && <p style={errorStyle}>{error}</p>}
    </div>
  );
}
