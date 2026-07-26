import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useUserProfile } from "@/context/user_profile_context";
import type { CVProfileDraft } from "../types/cv_profile_draft";
import type { OnboardingResponse } from "../types/onboarding_response";
import { saveProfile, updateSearchQueries } from "../api/onboarding_api";
import CvUploadForm from "../components/cv_upload_form";
import LoadingStep from "../components/loading_step";
import ReviewStep from "../components/review_step";
import SearchQueriesStep from "../components/search_queries_step";
import type { ProfileFormValues } from "../components/profile_review_form";

type Step = "upload" | "loading" | "review" | "search_queries";

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: "#f9fafb",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  padding: "3rem 1.5rem",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
};

const cardStyle: React.CSSProperties = {
  background: "white",
  borderRadius: "0.75rem",
  boxShadow: "0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)",
  padding: "2.5rem",
  width: "100%",
  maxWidth: "780px",
};

const headerStyle: React.CSSProperties = {
  marginBottom: "2rem",
  paddingBottom: "1.5rem",
  borderBottom: "1px solid #e5e7eb",
};

const titleStyle: React.CSSProperties = {
  fontSize: "1.875rem",
  fontWeight: 800,
  color: "#111827",
  margin: "0 0 0.375rem",
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  color: "#6b7280",
  margin: 0,
};

const uploadTitleStyle: React.CSSProperties = {
  fontSize: "1.25rem",
  fontWeight: 700,
  color: "#111827",
  margin: "0 0 1.25rem",
};

const apiErrorStyle: React.CSSProperties = {
  padding: "0.875rem 1rem",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: "0.375rem",
  color: "#b91c1c",
  fontSize: "0.875rem",
  marginBottom: "1.25rem",
};

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const defaultEmail = searchParams.get("email") ?? undefined;
  const { refetch } = useUserProfile();
  const [step, setStep] = useState<Step>("upload");
  const [draft, setDraft] = useState<CVProfileDraft | null>(null);
  const [cvRawText, setCvRawText] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [savedProfileId, setSavedProfileId] = useState<string | null>(null);
  const [generatedQueries, setGeneratedQueries] = useState<string[]>([]);

  const saveProfileMutation = useMutation({
    mutationFn: saveProfile,
    onSuccess: (result) => {
      setSavedProfileId(result.profile_id);
      setGeneratedQueries(result.search_queries ?? []);
      setStep("search_queries");
    },
    onError: (error: Error) => {
      setApiError(error.message);
      setStep("review");
    },
  });

  const updateQueriesMutation = useMutation({
    mutationFn: ({ profileId, queries }: { profileId: string; queries: string[] }) =>
      updateSearchQueries(profileId, queries),
    onSuccess: async () => {
      await refetch();
      navigate("/dashboard");
    },
    onError: (error: Error) => {
      setApiError(error.message);
    },
  });

  const handleAnalyzeStart = () => {
    setApiError(null);
    setStep("loading");
  };

  const handleAnalyzeSuccess = (data: OnboardingResponse) => {
    setDraft(data.cv_profile);
    setCvRawText(data.cv_raw_text);
    setStep("review");
  };

  const handleAnalyzeError = (message: string) => {
    setApiError(message);
    setStep("upload");
  };

  const handleConfirm = (values: ProfileFormValues) => {
    if (!cvRawText) return;
    setApiError(null);
    saveProfileMutation.mutate({
      cv_profile: values as CVProfileDraft,
      cv_raw_text: cvRawText,
    });
  };

  const handleQueriesConfirm = (queries: string[]) => {
    if (!savedProfileId) return;
    setApiError(null);
    updateQueriesMutation.mutate({ profileId: savedProfileId, queries });
  };

  return (
    <div style={pageStyle}>
      <div style={cardStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>Mission Radar AI</h1>
          <p style={subtitleStyle}>
            Set up your profile to start receiving matched missions
          </p>
        </div>

        {step === "upload" && (
          <>
            <h2 style={uploadTitleStyle}>Upload your CV</h2>
            {apiError && <div style={apiErrorStyle}>{apiError}</div>}
            <CvUploadForm
              defaultEmail={defaultEmail}
              onAnalyzeStart={handleAnalyzeStart}
              onAnalyzeSuccess={handleAnalyzeSuccess}
              onAnalyzeError={handleAnalyzeError}
            />
          </>
        )}

        {(step === "loading" || saveProfileMutation.isPending) && <LoadingStep />}

        {step === "review" && draft && !saveProfileMutation.isPending && (
          <>
            {apiError && <div style={apiErrorStyle}>{apiError}</div>}
            <ReviewStep draft={draft} onConfirm={handleConfirm} />
          </>
        )}

        {step === "search_queries" && (
          <>
            {apiError && <div style={apiErrorStyle}>{apiError}</div>}
            <SearchQueriesStep
              initialQueries={generatedQueries}
              onConfirm={handleQueriesConfirm}
              isPending={updateQueriesMutation.isPending}
            />
          </>
        )}
      </div>
    </div>
  );
}
