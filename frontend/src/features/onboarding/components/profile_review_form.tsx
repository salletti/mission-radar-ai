import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { CVProfileDraft } from "../types/cv_profile_draft";
import SkillsInput from "./skills_input";

export const CONTRACT_TYPES = [
  { value: "freelance", label: "Freelance" },
  { value: "permanent", label: "CDI" },
  { value: "fixed_term", label: "CDD" },
  { value: "internship", label: "Stage" },
  { value: "apprenticeship", label: "Alternance" },
  { value: "unknown", label: "Non précisé" },
];

export const REMOTE_MODES = [
  { value: "full_remote", label: "Full Remote" },
  { value: "hybrid", label: "Hybride" },
  { value: "onsite", label: "Présentiel" },
  { value: "unknown", label: "Non précisé" },
];

export const profileSchema = z.object({
  email: z.string().email("Valid email required"),
  full_name: z.string().min(1, "Full name is required"),
  title: z.string().min(1, "Title is required"),
  years_experience: z.coerce
    .number({ invalid_type_error: "Must be a number" })
    .int()
    .min(0, "Must be ≥ 0"),
  preferred_contract_type: z.string().min(1, "Contract type is required"),
  target_tjm: z.coerce
    .number({ invalid_type_error: "Must be a number" })
    .positive("Must be > 0"),
  preferred_remote_mode: z.string().min(1, "Remote mode is required"),
  location: z.string().nullable().optional(),
  skills: z.array(z.string().min(1)).min(1, "At least one skill is required"),
  availability: z.string().min(1, "Availability is required"),
});

export type ProfileFormValues = z.infer<typeof profileSchema>;

const gridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "1.25rem",
};

const fieldStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.375rem",
};

const fullWidthStyle: React.CSSProperties = {
  ...fieldStyle,
  gridColumn: "1 / -1",
};

const labelStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  fontWeight: 600,
  color: "#374151",
};

const inputStyle: React.CSSProperties = {
  padding: "0.625rem 0.75rem",
  border: "1px solid #d1d5db",
  borderRadius: "0.375rem",
  fontSize: "0.875rem",
  outline: "none",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  background: "white",
  cursor: "pointer",
};

const errorStyle: React.CSSProperties = {
  color: "#ef4444",
  fontSize: "0.875rem",
  margin: 0,
};

const submitBtnStyle: React.CSSProperties = {
  gridColumn: "1 / -1",
  padding: "0.875rem 2rem",
  background: "#059669",
  color: "white",
  border: "none",
  borderRadius: "0.375rem",
  fontSize: "1rem",
  fontWeight: 600,
  cursor: "pointer",
  marginTop: "0.5rem",
};

interface ProfileReviewFormProps {
  draft: CVProfileDraft;
  onConfirm: (values: ProfileFormValues) => void;
}

export default function ProfileReviewForm({
  draft,
  onConfirm,
}: ProfileReviewFormProps) {
  const availabilityDate = draft.availability.includes("T")
    ? draft.availability.split("T")[0]
    : draft.availability;

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      email: draft.email,
      full_name: draft.full_name,
      title: draft.title,
      years_experience: draft.years_experience,
      preferred_contract_type: draft.preferred_contract_type,
      target_tjm: draft.target_tjm,
      preferred_remote_mode: draft.preferred_remote_mode,
      location: draft.location ?? "",
      skills: draft.skills,
      availability: availabilityDate,
    },
  });

  return (
    <form style={gridStyle} onSubmit={handleSubmit(onConfirm)}>
      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="r-email">
          Email
        </label>
        <input
          id="r-email"
          type="email"
          style={inputStyle}
          {...register("email")}
        />
        {errors.email && <p style={errorStyle}>{errors.email.message}</p>}
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="r-full-name">
          Full Name
        </label>
        <input
          id="r-full-name"
          type="text"
          style={inputStyle}
          {...register("full_name")}
        />
        {errors.full_name && (
          <p style={errorStyle}>{errors.full_name.message}</p>
        )}
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="r-title">
          Title
        </label>
        <input
          id="r-title"
          type="text"
          style={inputStyle}
          {...register("title")}
        />
        {errors.title && <p style={errorStyle}>{errors.title.message}</p>}
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="r-years">
          Years of Experience
        </label>
        <input
          id="r-years"
          type="number"
          min={0}
          style={inputStyle}
          {...register("years_experience")}
        />
        {errors.years_experience && (
          <p style={errorStyle}>{errors.years_experience.message}</p>
        )}
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="r-contract">
          Contract Type
        </label>
        <select id="r-contract" style={selectStyle} {...register("preferred_contract_type")}>
          {CONTRACT_TYPES.map((ct) => (
            <option key={ct.value} value={ct.value}>
              {ct.label}
            </option>
          ))}
        </select>
        {errors.preferred_contract_type && (
          <p style={errorStyle}>{errors.preferred_contract_type.message}</p>
        )}
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="r-tjm">
          Target TJM (€/day)
        </label>
        <input
          id="r-tjm"
          type="number"
          min={1}
          style={inputStyle}
          {...register("target_tjm")}
        />
        {errors.target_tjm && (
          <p style={errorStyle}>{errors.target_tjm.message}</p>
        )}
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="r-remote">
          Remote Mode
        </label>
        <select id="r-remote" style={selectStyle} {...register("preferred_remote_mode")}>
          {REMOTE_MODES.map((rm) => (
            <option key={rm.value} value={rm.value}>
              {rm.label}
            </option>
          ))}
        </select>
        {errors.preferred_remote_mode && (
          <p style={errorStyle}>{errors.preferred_remote_mode.message}</p>
        )}
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="r-location">
          Location
        </label>
        <input
          id="r-location"
          type="text"
          style={inputStyle}
          placeholder="e.g. Paris, Lyon..."
          {...register("location")}
        />
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="r-availability">
          Availability
        </label>
        <input
          id="r-availability"
          type="date"
          style={inputStyle}
          {...register("availability")}
        />
        {errors.availability && (
          <p style={errorStyle}>{errors.availability.message}</p>
        )}
      </div>

      <div style={fullWidthStyle}>
        <label style={labelStyle}>Skills</label>
        <Controller
          name="skills"
          control={control}
          render={({ field }) => (
            <SkillsInput
              value={field.value}
              onChange={field.onChange}
              error={errors.skills?.root?.message ?? errors.skills?.message}
            />
          )}
        />
      </div>

      <button type="submit" style={submitBtnStyle}>
        Confirm Profile
      </button>
    </form>
  );
}
