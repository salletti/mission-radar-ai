import { useQuery } from "@tanstack/react-query";
import { get } from "@/api/client";
import { useUserProfile } from "@/context/user_profile_context";
import type { ActivityHistoryPage } from "@/features/history/types/activity_event";

const LIMIT = 20;

export function useHistory(page = 0) {
  const { profileId } = useUserProfile();

  return useQuery<ActivityHistoryPage>({
    queryKey: ["history", profileId, page],
    queryFn: () =>
      get<ActivityHistoryPage>("/api/dashboard/history", {
        user_profile_id: profileId ?? undefined,
        offset: page * LIMIT,
        limit: LIMIT,
      }),
    enabled: profileId !== null,
  });
}

export { LIMIT as HISTORY_PAGE_LIMIT };
