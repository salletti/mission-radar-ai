import { useQuery } from "@tanstack/react-query";
import { getPipelineRun } from "../api/pipeline_api";

export function usePipelineRun(id: string | null) {
  return useQuery({
    queryKey: ["pipeline", id],
    queryFn: () => getPipelineRun(id!),
    enabled: id !== null,
  });
}
