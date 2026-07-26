import React, { type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "@/api/client";
import { usePipelinePolling } from "./use_pipeline_polling";
import type { PipelineRun } from "../types/pipeline_run";

vi.mock("@/api/client");

const mockRun = (status: PipelineRun["status"]): PipelineRun => ({
  id: "run-1",
  user_id: "user-1",
  pipeline_type: "mission_refresh",
  trigger_type: "user",
  status,
  current_step: status === "completed" ? "done" : "collect",
  progress: status === "completed" ? 1.0 : 0.33,
  started_at: null,
  finished_at: status === "completed" ? "2026-06-28T12:00:00Z" : null,
  error_message: null,
  created_at: "2026-06-28T11:00:00Z",
});

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe("usePipelinePolling", () => {
  beforeEach(() => vi.clearAllMocks());

  it("does not fetch when id is null", () => {
    const { result } = renderHook(() => usePipelinePolling(null), {
      wrapper: makeWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(vi.mocked(client.get)).not.toHaveBeenCalled();
  });

  it("calls GET /api/pipelines/{id} when id is provided", async () => {
    vi.mocked(client.get).mockResolvedValue(mockRun("running"));

    const { result } = renderHook(() => usePipelinePolling("run-1"), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(vi.mocked(client.get)).toHaveBeenCalledWith("/api/pipelines/run-1");
  });

  it("invalidates ['missions'] and ['dashboard'] when status becomes completed", async () => {
    vi.mocked(client.get).mockResolvedValue(mockRun("completed"));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    function Wrapper({ children }: { children: ReactNode }) {
      return React.createElement(
        QueryClientProvider,
        { client: queryClient },
        children
      );
    }

    renderHook(() => usePipelinePolling("run-1"), { wrapper: Wrapper });

    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["missions"] })
    );
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard"] });
  });

  it("does NOT invalidate queries when status is failed", async () => {
    vi.mocked(client.get).mockResolvedValue(mockRun("failed"));

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    function Wrapper({ children }: { children: ReactNode }) {
      return React.createElement(
        QueryClientProvider,
        { client: queryClient },
        children
      );
    }

    const { result } = renderHook(() => usePipelinePolling("run-1"), {
      wrapper: Wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const hasMissionsCall = invalidateSpy.mock.calls.some(
      (args) =>
        JSON.stringify(args[0]) === JSON.stringify({ queryKey: ["missions"] })
    );
    expect(hasMissionsCall).toBe(false);
  });

  describe("polling interval", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it("polls every 2s while status is running", async () => {
      vi.mocked(client.get).mockResolvedValue(mockRun("running"));

      renderHook(() => usePipelinePolling("run-1"), { wrapper: makeWrapper() });

      await vi.advanceTimersByTimeAsync(100);
      expect(vi.mocked(client.get)).toHaveBeenCalledTimes(1);

      await vi.advanceTimersByTimeAsync(2000);
      expect(vi.mocked(client.get)).toHaveBeenCalledTimes(2);

      await vi.advanceTimersByTimeAsync(2000);
      expect(vi.mocked(client.get)).toHaveBeenCalledTimes(3);
    });

    it("stops polling when status becomes completed", async () => {
      vi.mocked(client.get)
        .mockResolvedValueOnce(mockRun("running"))
        .mockResolvedValueOnce(mockRun("completed"));

      renderHook(() => usePipelinePolling("run-1"), { wrapper: makeWrapper() });

      await vi.advanceTimersByTimeAsync(100);
      await vi.advanceTimersByTimeAsync(2000);
      await vi.advanceTimersByTimeAsync(100);

      const callCount = vi.mocked(client.get).mock.calls.length;
      await vi.advanceTimersByTimeAsync(6000);
      expect(vi.mocked(client.get)).toHaveBeenCalledTimes(callCount);
    });

    it("stops polling when status becomes failed", async () => {
      vi.mocked(client.get)
        .mockResolvedValueOnce(mockRun("running"))
        .mockResolvedValueOnce(mockRun("failed"));

      renderHook(() => usePipelinePolling("run-1"), { wrapper: makeWrapper() });

      await vi.advanceTimersByTimeAsync(100);
      await vi.advanceTimersByTimeAsync(2000);
      await vi.advanceTimersByTimeAsync(100);

      const callCount = vi.mocked(client.get).mock.calls.length;
      await vi.advanceTimersByTimeAsync(6000);
      expect(vi.mocked(client.get)).toHaveBeenCalledTimes(callCount);
    });
  });
});
