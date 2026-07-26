import type { CVProfileDraft } from "./cv_profile_draft";

export interface OnboardingResponse {
  cv_profile: CVProfileDraft;
  cv_raw_text: string;
}
