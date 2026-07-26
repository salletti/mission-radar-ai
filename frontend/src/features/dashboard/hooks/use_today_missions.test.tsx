import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UserProfileContext } from "@/context/user_profile_context";
import { useTodayMissions } from "./use_today_missions";
import * as client from "@/api/client";
import type { TodayMission } from "../types/mission";

vi.mock("@/api/client");

const mockMission: TodayMission = {
  mission_match_id: "m-1",
  analyzed_post_id: "ap-1",
  raw_post_id: "rp-1",
  author_name: "Bob",
  content_excerpt: "Freelance mission React",
  post_url: "https://linkedin.com/posts/bob",
  detected_stack: ["React"],
  detected_contract_type: "freelance",
  detected_remote_mode: "full_remote",
  global_score: 0.75,
  score_details: { semantic: 0.8, contract: 0.7, tjm: 0.6, remote: 0.9 },
  detected_tjm: 600,
  title: null,
  company: null,
  location: null,
};

function createWrapper(profileId: string | null = "test-profile-uuid") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <UserProfileContext.Provider
        value={{
          profileId,
          userEmail: null,
          isLoading: false,
          needsOnboarding: false,
          refetch: async () => {},
        }}
      >
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </UserProfileContext.Provider>
    );
  };
}

describe("useTodayMissions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("is disabled when profileId is null — GET is not called", () => {
    const wrapper = createWrapper(null);
    const { result } = renderHook(() => useTodayMissions(), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(vi.mocked(client.get)).not.toHaveBeenCalled();
  });

  it("calls GET /api/dashboard/missions/today with correct params when profileId exists", async () => {
    vi.mocked(client.get).mockResolvedValue([]);
    const wrapper = createWrapper("test-profile-uuid");

    const { result } = renderHook(() => useTodayMissions(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(vi.mocked(client.get)).toHaveBeenCalledWith(
      "/api/dashboard/missions/today",
      {
        user_profile_id: "test-profile-uuid",
        min_score: 0.5,
        limit: 20,
      }
    );
  });

  it("returns data from the API client", async () => {
    vi.mocked(client.get).mockResolvedValue([mockMission]);
    const wrapper = createWrapper("test-profile-uuid");

    const { result } = renderHook(() => useTodayMissions(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([mockMission]);
  });

  it("exposes error state when GET fails", async () => {
    vi.mocked(client.get).mockRejectedValue(new Error("Network error"));
    const wrapper = createWrapper("test-profile-uuid");

    const { result } = renderHook(() => useTodayMissions(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
  });
});
