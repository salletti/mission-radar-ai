import { type ChangeEvent } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { uploadCv } from "../api/onboarding_api";
import type { OnboardingResponse } from "../types/onboarding_response";

const uploadSchema = z.object({
  email: z.string().email("Valid email required"),
  file: z
    .any()
    .refine((f): f is File => f instanceof File && f.size > 0, "PDF file required")
    .refine(
      (f) => !(f instanceof File) || f.name.toLowerCase().endsWith(".pdf"),
      "Only PDF files are accepted"
    ),
});

interface UploadFormValues {
  email: string;
  file: File;
}

const formStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "1.25rem",
};

const fieldStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.375rem",
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

const errorStyle: React.CSSProperties = {
  color: "#ef4444",
  fontSize: "0.875rem",
  margin: 0,
};

const submitBtnStyle: React.CSSProperties = {
  padding: "0.75rem 1.5rem",
  background: "#4f46e5",
  color: "white",
  border: "none",
  borderRadius: "0.375rem",
  fontSize: "0.875rem",
  fontWeight: 600,
  cursor: "pointer",
};

const submitBtnDisabledStyle: React.CSSProperties = {
  ...submitBtnStyle,
  background: "#9ca3af",
  cursor: "not-allowed",
  opacity: 0.7,
};

interface CvUploadFormProps {
  defaultEmail?: string;
  onAnalyzeStart: () => void;
  onAnalyzeSuccess: (data: OnboardingResponse) => void;
  onAnalyzeError: (message: string) => void;
}

export default function CvUploadForm({
  defaultEmail,
  onAnalyzeStart,
  onAnalyzeSuccess,
  onAnalyzeError,
}: CvUploadFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: { email: defaultEmail ?? "" },
  });

  const { mutate, isPending } = useMutation({
    mutationFn: ({ email, file }: UploadFormValues) => uploadCv(email, file),
    onMutate: () => onAnalyzeStart(),
    onSuccess: (data) => onAnalyzeSuccess(data),
    onError: (err: Error) => onAnalyzeError(err.message),
  });

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setValue("file", file, { shouldValidate: false });
    }
  };

  return (
    <form style={formStyle} noValidate onSubmit={handleSubmit((data) => mutate(data))}>
      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          style={inputStyle}
          disabled={isPending}
          {...register("email")}
        />
        {errors.email && <p style={errorStyle}>{errors.email.message}</p>}
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="file">
          CV (PDF)
        </label>
        <input
          id="file"
          type="file"
          accept=".pdf"
          disabled={isPending}
          onChange={handleFileChange}
        />
        {errors.file && (
          <p style={errorStyle}>{errors.file.message as string}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={isPending}
        style={isPending ? submitBtnDisabledStyle : submitBtnStyle}
      >
        {isPending ? "Analyzing..." : "Analyze CV"}
      </button>
    </form>
  );
}
