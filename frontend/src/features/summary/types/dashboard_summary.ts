export interface DashboardKpis {
  total_missions: number;
  new_today: number;
  average_score: number;
  last_refresh: string | null;
  pipeline_status: string | null;
}

export interface PipelineHealth {
  status: string;
  last_pipeline_duration_seconds: number | null;
}

export interface DashboardSummary {
  kpis: DashboardKpis;
  health: PipelineHealth;
}
