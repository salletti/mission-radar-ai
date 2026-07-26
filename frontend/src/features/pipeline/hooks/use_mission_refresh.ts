import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useUserProfile } from "@/context/user_profile_context";
import { startMissionRefresh } from "../api/pipeline_api";
import { usePipelinePolling } from "./use_pipeline_polling";
import type { PipelineStatus } from "../types/pipeline_run";

const TERMINAL_STATUSES: PipelineStatus[] = [
  "completed",
  "failed",
  "cancelled",
];

export function useMissionRefresh() {
  const { profileId } = useUserProfile();
  const runKey = `mission_radar_pipeline_${profileId}`;
  const syncKey = `mission_radar_last_sync_${profileId}`;

  const [pipelineRunId, setPipelineRunId] = useState<string | null>(() =>
    profileId ? localStorage.getItem(runKey) : null
  );
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(() =>
    profileId ? localStorage.getItem(syncKey) : null
  );

  const pollingQuery = usePipelinePolling(pipelineRunId);

  useEffect(() => {
    const status = pollingQuery.data?.status;
    if (status === "completed") {
      const ts =
        pollingQuery.data.finished_at ?? new Date().toISOString();
      setLastSyncAt(ts);
      localStorage.setItem(syncKey, ts);
      localStorage.removeItem(runKey);
      setPipelineRunId(null);
    }
    if (status === "failed" || status === "cancelled") {
      localStorage.removeItem(runKey);
      setPipelineRunId(null);
    }
  }, [pollingQuery.data?.status, runKey, syncKey]);

  useEffect(() => {
    if (pollingQuery.isError) {
      localStorage.removeItem(runKey);
      setPipelineRunId(null);
    }
  }, [pollingQuery.isError, runKey]);

  const mutation = useMutation({
    mutationFn: () => startMissionRefresh(),
    onSuccess: (data) => {
      localStorage.setItem(runKey, data.id);
      setPipelineRunId(data.id);
    },
  });

  useEffect(() => {
    if (pollingQuery.isTimedOut) {
      localStorage.removeItem(runKey);
      setPipelineRunId(null);
    }
  }, [pollingQuery.isTimedOut, runKey]);

  const currentStatus = pollingQuery.data?.status;
  const isTerminal =
    currentStatus !== undefined && TERMINAL_STATUSES.includes(currentStatus);
  const isPolling = pipelineRunId !== null && !isTerminal;

  return {
    pipelineRun: pollingQuery.data ?? null,
    lastSyncAt,
    isPolling,
    isTimedOut: pollingQuery.isTimedOut,
    isStarting: mutation.isPending,
    startError: mutation.error,
    pollingError: pollingQuery.error,
    startRefresh: () => mutation.mutate(),
  };
}
