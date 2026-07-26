import { useQuery } from "@tanstack/react-query";
import { get } from "@/api/client";
import { useUserProfile } from "@/context/user_profile_context";
import type { DashboardSummary } from "../types/dashboard_summary";

export function useDashboardSummary() {
  const { profileId } = useUserProfile();

  return useQuery<DashboardSummary>({
    queryKey: ["dashboard", "summary", profileId],
    queryFn: () =>
      get<DashboardSummary>("/api/dashboard/summary", {
        user_profile_id: profileId ?? undefined,
      }),
    enabled: profileId !== null,
  });
}
