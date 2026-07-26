import { useQuery } from "@tanstack/react-query";
import { get } from "@/api/client";
import { useUserProfile } from "@/context/user_profile_context";
import type { TodayMission } from "../types/mission";

export function useTodayMissions() {
  const { profileId } = useUserProfile();

  return useQuery<TodayMission[]>({
    queryKey: ["missions", "today", profileId],
    queryFn: () =>
      get<TodayMission[]>("/api/dashboard/missions/today", {
        user_profile_id: profileId ?? undefined,
        min_score: 0.5,
        limit: 20,
      }),
    enabled: profileId !== null,
  });
}
