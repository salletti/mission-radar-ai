export interface CVProfileDraft {
  email: string;
  full_name: string;
  title: string;
  years_experience: number;
  preferred_contract_type: string;
  target_tjm: number;
  preferred_remote_mode: string;
  location: string | null;
  skills: string[];
  availability: string;
}
