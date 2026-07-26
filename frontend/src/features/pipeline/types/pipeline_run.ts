export type PipelineStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type PipelineStep = "collect" | "analyze" | "match" | "done";

export interface PipelineRun {
  id: string;
  user_id: string;
  pipeline_type: string;
  trigger_type: string;
  status: PipelineStatus;
  current_step: PipelineStep;
  progress: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
}
