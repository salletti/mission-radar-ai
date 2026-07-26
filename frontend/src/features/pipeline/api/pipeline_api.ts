import { get, post } from "@/api/client";
import type { PipelineRun } from "../types/pipeline_run";

export function startMissionRefresh(): Promise<PipelineRun> {
  return post<PipelineRun>("/api/pipelines/mission-refresh", undefined);
}

export function getPipelineRun(id: string): Promise<PipelineRun> {
  return get<PipelineRun>(`/api/pipelines/${id}`);
}
