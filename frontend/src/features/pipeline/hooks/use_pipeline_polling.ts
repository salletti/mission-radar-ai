import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getPipelineRun } from "../api/pipeline_api";
import type { PipelineStatus } from "../types/pipeline_run";

const TERMINAL_STATUSES: PipelineStatus[] = [
  "completed",
  "failed",
  "cancelled",
];

const POLL_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

export function usePipelinePolling(id: string | null) {
  const queryClient = useQueryClient();
  const pollStartRef = useRef<number | null>(null);

  const query = useQuery({
    queryKey: ["pipeline", id],
    queryFn: () => getPipelineRun(id!),
    enabled: id !== null,
    staleTime: Infinity,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (!status || TERMINAL_STATUSES.includes(status)) return false;
      if (pollStartRef.current === null) pollStartRef.current = Date.now();
      if (Date.now() - pollStartRef.current > POLL_TIMEOUT_MS) return false;
      return 2000;
    },
  });

  // Reset timer when a new pipeline id is tracked
  useEffect(() => {
    pollStartRef.current = null;
  }, [id]);

  useEffect(() => {
    if (query.data?.status === "completed") {
      queryClient.invalidateQueries({ queryKey: ["missions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    }
  }, [query.data?.status, queryClient]);

  const isTimedOut =
    id !== null &&
    pollStartRef.current !== null &&
    !TERMINAL_STATUSES.includes(query.data?.status ?? "pending") &&
    Date.now() - pollStartRef.current > POLL_TIMEOUT_MS;

  return { ...query, isTimedOut };
}
