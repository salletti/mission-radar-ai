import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UserProfileContext } from "@/context/user_profile_context";
import { useMission } from "./use_mission";
import * as client from "@/api/client";
import type { MissionDetail } from "../types/mission_detail";

vi.mock("@/api/client");

const mockDetail: MissionDetail = {
  mission_match_id: "m-1",
  analyzed_post_id: "ap-1",
  raw_post_id: "rp-1",
  author_name: "Alice",
  content_excerpt: "Mission Python",
  post_url: "https://linkedin.com/posts/1",
  detected_stack: ["python", "fastapi"],
  detected_contract_type: "freelance",
  detected_remote_mode: "full_remote",
  global_score: 0.85,
  score_details: { semantic: 0.9, contract: 1.0, tjm: 0.7, remote: 1.0 },
  detected_tjm: 700,
  title: "Senior Python Engineer",
  company: "Acme",
  location: "Paris",
  author_url: "https://linkedin.com/in/alice",
  content: "Mission Python FastAPI full remote",
  published_at: "2026-06-01T10:00:00Z",
  summary: "Mission Python full remote 700€/j.",
  seniority: "senior",
  matched_at: "2026-06-28T10:00:00Z",
  matched_skills: ["python", "fastapi"],
  missing_skills: ["kubernetes"],
  explainability_hints: ["Votre expérience python correspond à la stack demandée."],
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

describe("useMission", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("is disabled when profileId is null", () => {
    const wrapper = createWrapper(null);
    const { result } = renderHook(() => useMission("m-1"), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(vi.mocked(client.get)).not.toHaveBeenCalled();
  });

  it("is disabled when id is empty", () => {
    const wrapper = createWrapper("test-profile-uuid");
    const { result } = renderHook(() => useMission(""), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
  });

  it("calls GET /api/dashboard/missions/:id with correct params", async () => {
    vi.mocked(client.get).mockResolvedValue(mockDetail);
    const wrapper = createWrapper("test-profile-uuid");

    const { result } = renderHook(() => useMission("m-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(vi.mocked(client.get)).toHaveBeenCalledWith("/api/dashboard/missions/m-1", {
      user_profile_id: "test-profile-uuid",
    });
  });

  it("returns mission detail data from the API", async () => {
    vi.mocked(client.get).mockResolvedValue(mockDetail);
    const wrapper = createWrapper("test-profile-uuid");

    const { result } = renderHook(() => useMission("m-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockDetail);
  });

  it("exposes error state when GET fails", async () => {
    vi.mocked(client.get).mockRejectedValue(new Error("Not found"));
    const wrapper = createWrapper("test-profile-uuid");

    const { result } = renderHook(() => useMission("m-1"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
  });
});
