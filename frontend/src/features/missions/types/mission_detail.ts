import type { TodayMission } from "@/features/dashboard/types/mission";

export interface ScoreBreakdown {
  skills: number | null;
  experience: number | null;
  location: number | null;
  contract: number | null;
  daily_rate: number | null;
}

export interface Explanation {
  score_breakdown: ScoreBreakdown;
  matching_reasons: string[];
  warnings: string[];
  strong_points: string[];
  missing_skills: string[];
  recommendations: string[];
}

export interface MissionDetail extends TodayMission {
  author_url: string;
  content: string;
  published_at: string;
  summary: string;
  seniority: string | null;
  matched_at: string;
  matched_skills: string[];
  missing_skills: string[];
  explanation: Explanation;
}
