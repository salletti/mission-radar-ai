import { useQuery } from "@tanstack/react-query";
import { get } from "@/api/client";
import { useUserProfile } from "@/context/user_profile_context";
import type { TodayMission } from "@/features/dashboard/types/mission";

interface HistoryOptions {
  minScore?: number;
  limit?: number;
  offset?: number;
}

export function useMissionHistory(options?: HistoryOptions) {
  const { profileId } = useUserProfile();

  return useQuery<TodayMission[]>({
    queryKey: ["missions", "history", profileId, options],
    queryFn: () =>
      get<TodayMission[]>("/api/dashboard/missions/history", {
        user_profile_id: profileId ?? undefined,
        min_score: options?.minScore,
        limit: options?.limit ?? 50,
        offset: options?.offset ?? 0,
      }),
    enabled: profileId !== null,
  });
}
