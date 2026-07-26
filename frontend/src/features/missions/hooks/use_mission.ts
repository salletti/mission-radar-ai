import { useQuery } from "@tanstack/react-query";
import { get } from "@/api/client";
import { useUserProfile } from "@/context/user_profile_context";
import type { MissionDetail } from "../types/mission_detail";

export function useMission(id: string) {
  const { profileId } = useUserProfile();

  return useQuery<MissionDetail>({
    queryKey: ["missions", "detail", id, profileId],
    queryFn: () =>
      get<MissionDetail>(`/api/dashboard/missions/${id}`, {
        user_profile_id: profileId ?? undefined,
      }),
    enabled: profileId !== null && id !== "",
  });
}
