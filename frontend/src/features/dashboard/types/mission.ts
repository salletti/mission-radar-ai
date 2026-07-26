export interface ScoreDetails {
  semantic: number;
  contract: number;
  tjm: number;
  remote: number;
}

export interface TodayMission {
  mission_match_id: string;
  analyzed_post_id: string;
  raw_post_id: string;
  author_name: string;
  content_excerpt: string;
  post_url: string;
  detected_stack: string[];
  detected_contract_type: string;
  detected_remote_mode: string;
  global_score: number;
  score_details: ScoreDetails;
  detected_tjm: number | null;
  title: string | null;
  company: string | null;
  location: string | null;
}
