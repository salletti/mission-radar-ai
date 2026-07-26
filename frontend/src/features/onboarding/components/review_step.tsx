import type { CVProfileDraft } from "../types/cv_profile_draft";
import ProfileReviewForm, {
  type ProfileFormValues,
} from "./profile_review_form";

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
  margin: 0,
};

interface ReviewStepProps {
  draft: CVProfileDraft;
  onConfirm: (values: ProfileFormValues) => void;
}

export default function ReviewStep({ draft, onConfirm }: ReviewStepProps) {
  return (
    <div style={containerStyle}>
      <div>
        <h2 style={headingStyle}>Review Your Profile</h2>
        <p style={subtitleStyle}>
          The AI extracted the following information from your CV. Review and
          edit any field before confirming.
        </p>
      </div>
      <ProfileReviewForm draft={draft} onConfirm={onConfirm} />
    </div>
  );
}
