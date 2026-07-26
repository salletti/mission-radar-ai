import { Auth0Provider, useAuth0, type AppState } from "@auth0/auth0-react";
import { useEffect, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { setAuthTokenGetter } from "@/api/auth_token";

const domain = import.meta.env.VITE_AUTH0_DOMAIN;
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID;
const audience = import.meta.env.VITE_AUTH0_AUDIENCE;

// Wires useAuth0().getAccessTokenSilently into the module-level getter that
// api/client.ts reads from — client.ts's get()/post() are plain async
// functions, not hooks, so they can't call useAuth0() directly.
function AuthTokenBridge() {
  const { isAuthenticated, getAccessTokenSilently } = useAuth0();

  useEffect(() => {
    if (!isAuthenticated) {
      setAuthTokenGetter(async () => null);
      return;
    }
    setAuthTokenGetter(async () => {
      try {
        return await getAccessTokenSilently();
      } catch {
        return null;
      }
    });
  }, [isAuthenticated, getAccessTokenSilently]);

  return null;
}

export function Auth0ProviderWithNavigate({
  children,
}: {
  children: ReactNode;
}) {
  const navigate = useNavigate();

  // Auth0 not configured yet (Phase 10.4.1 not completed in this environment)
  // — render children unauthenticated rather than crashing the whole app.
  if (!(domain && clientId && audience)) {
    return <>{children}</>;
  }

  const onRedirectCallback = (appState?: AppState) => {
    navigate(appState?.returnTo ?? window.location.pathname);
  };

  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience,
      }}
      onRedirectCallback={onRedirectCallback}
      useRefreshTokens={true}
      cacheLocation="localstorage"
    >
      <AuthTokenBridge />
      {children}
    </Auth0Provider>
  );
}
