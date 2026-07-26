// Bridges Auth0's hook-based getAccessTokenSilently() into the plain async
// get()/post() functions in client.ts, which aren't React components/hooks.
// Set once by AuthTokenBridge (see app/providers/auth0_provider.tsx).
type TokenGetter = () => Promise<string | null>;

let tokenGetter: TokenGetter = async () => null;

export function setAuthTokenGetter(getter: TokenGetter): void {
  tokenGetter = getter;
}

export async function getAuthToken(): Promise<string | null> {
  return tokenGetter();
}
