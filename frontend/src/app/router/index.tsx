import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useUserProfile, UserProfileProvider } from "@/context/user_profile_context";
import { Auth0ProviderWithNavigate } from "@/app/providers/auth0_provider";
import DashboardLayout from "@/shared/components/layouts/dashboard_layout";
import LoginPage from "@/features/auth/pages/login_page";
import OnboardingPage from "@/features/onboarding/pages/onboarding_page";
import DashboardPage from "@/features/dashboard/pages/dashboard_page";
import MissionDetailPage from "@/features/missions/pages/mission_detail_page";
import HistoryPage from "@/features/history/pages/history_page";

function LandingRoute() {
  const { profileId, needsOnboarding, isLoading } = useUserProfile();
  if (isLoading) return null;
  if (profileId) return <Navigate to="/dashboard" replace />;
  if (needsOnboarding) return <Navigate to="/onboarding" replace />;
  return <LoginPage />;
}

function RequireProfile() {
  const { profileId, needsOnboarding, isLoading } = useUserProfile();
  if (isLoading) return null;
  if (needsOnboarding) return <Navigate to="/onboarding" replace />;
  if (!profileId) return <Navigate to="/" replace />;
  return <Outlet />;
}

function OnboardingRoute() {
  const { profileId, isLoading } = useUserProfile();
  if (isLoading) return null;
  if (profileId) return <Navigate to="/dashboard" replace />;
  return <OnboardingPage />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Auth0ProviderWithNavigate>
        <UserProfileProvider>
          <Routes>
            <Route index element={<LandingRoute />} />
            <Route path="/onboarding" element={<OnboardingRoute />} />
            <Route element={<RequireProfile />}>
              <Route element={<DashboardLayout />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/missions/:id" element={<MissionDetailPage />} />
                <Route path="/history" element={<HistoryPage />} />
              </Route>
            </Route>
          </Routes>
        </UserProfileProvider>
      </Auth0ProviderWithNavigate>
    </BrowserRouter>
  );
}
