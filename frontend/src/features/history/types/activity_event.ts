export type ActivityEventType = "MISSION_MATCH" | "DAILY_DIGEST";

export interface ActivityEvent {
  type: ActivityEventType;
  occurred_at: string;
  title: string;
  description: string;
  score: number; // MISSION_MATCH: 0-100%; DAILY_DIGEST: missions_count (≥0=SENT, -1=FAILED)
  mission_match_id?: string | null;
  digest_history_id?: string | null;
}

export interface ActivityHistoryPage {
  items: ActivityEvent[];
  total: number;
  limit: number;
  offset: number;
}
