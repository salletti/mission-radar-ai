import { authHeaders } from "@/api/client";
import type { CVProfileDraft } from "../types/cv_profile_draft";
import type { OnboardingResponse } from "../types/onboarding_response";

export interface SaveProfileRequest {
  cv_profile: CVProfileDraft;
  cv_raw_text: string;
}

export interface SaveProfileResult {
  profile_id: string;
  email: string;
  status: "created" | "updated";
  search_queries: string[];
}

export async function saveProfile(
  payload: SaveProfileRequest
): Promise<SaveProfileResult> {
  const response = await fetch("/api/onboarding/profile", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail: string;
    try {
      const data = await response.json();
      detail =
        typeof data.detail === "string"
          ? data.detail
          : `Erreur ${response.status}`;
    } catch {
      detail = `Erreur ${response.status} — backend indisponible ou réponse non-JSON`;
    }
    throw new Error(detail);
  }

  return response.json() as Promise<SaveProfileResult>;
}

export async function updateSearchQueries(
  profileId: string,
  queries: string[]
): Promise<void> {
  const response = await fetch(
    `/api/onboarding/profile/${profileId}/search-queries`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...(await authHeaders()) },
      body: JSON.stringify({ queries }),
    }
  );

  if (!response.ok) {
    let detail: string;
    try {
      const data = await response.json();
      detail =
        typeof data.detail === "string"
          ? data.detail
          : `Erreur ${response.status}`;
    } catch {
      detail = `Erreur ${response.status} — backend indisponible ou réponse non-JSON`;
    }
    throw new Error(detail);
  }
}

export async function uploadCv(
  email: string,
  file: File
): Promise<OnboardingResponse> {
  const formData = new FormData();
  formData.append("email", email);
  formData.append("file", file);

  const response = await fetch("/api/onboarding/cv", {
    method: "POST",
    headers: await authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    let detail: string;
    try {
      const data = await response.json();
      detail =
        typeof data.detail === "string"
          ? data.detail
          : `Erreur ${response.status}`;
    } catch {
      detail = `Erreur ${response.status} — backend indisponible ou réponse non-JSON`;
    }
    throw new Error(detail);
  }

  return response.json() as Promise<OnboardingResponse>;
}
