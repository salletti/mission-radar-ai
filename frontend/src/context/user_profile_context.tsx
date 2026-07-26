import { useAuth0 } from "@auth0/auth0-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { ApiError } from "@/api/client";
import { getMe } from "@/api/users_api";

interface UserProfileContextValue {
  profileId: string | null;
  userEmail: string | null;
  isLoading: boolean;
  needsOnboarding: boolean;
  refetch: () => Promise<void>;
}

// Exported (not just useUserProfile) so tests can supply a fixed value via
// <UserProfileContext.Provider> directly, without needing Auth0 + network mocks.
export const UserProfileContext = createContext<UserProfileContextValue | null>(null);

export function UserProfileProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading: authLoading } = useAuth0();
  const [profileId, setProfileId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const refetch = useCallback(async () => {
    if (!isAuthenticated) {
      setProfileId(null);
      setUserEmail(null);
      setNeedsOnboarding(false);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    try {
      const me = await getMe();
      setProfileId(me.profile_id);
      setUserEmail(me.email);
      setNeedsOnboarding(false);
    } catch (err) {
      setProfileId(null);
      setUserEmail(null);
      setNeedsOnboarding(err instanceof ApiError && err.status === 404);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (authLoading) return;
    refetch();
  }, [authLoading, refetch]);

  return (
    <UserProfileContext.Provider
      value={{
        profileId,
        userEmail,
        isLoading: authLoading || isLoading,
        needsOnboarding,
        refetch,
      }}
    >
      {children}
    </UserProfileContext.Provider>
  );
}

export function useUserProfile(): UserProfileContextValue {
  const ctx = useContext(UserProfileContext);
  if (!ctx) {
    throw new Error("useUserProfile must be used within UserProfileProvider");
  }
  return ctx;
}
