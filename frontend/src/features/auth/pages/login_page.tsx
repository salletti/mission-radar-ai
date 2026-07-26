import { useAuth0 } from "@auth0/auth0-react";
import { useEffect, useState } from "react";

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: "#f9fafb",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  padding: "3rem 1.5rem",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
};

const cardStyle: React.CSSProperties = {
  background: "white",
  borderRadius: "0.75rem",
  boxShadow: "0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)",
  padding: "2.5rem",
  width: "100%",
  maxWidth: "480px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "1.875rem",
  fontWeight: 800,
  color: "#111827",
  margin: "0 0 0.375rem",
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "0.9375rem",
  color: "#6b7280",
  margin: "0 0 1.5rem",
};

const buttonStyle: React.CSSProperties = {
  background: "#4f46e5",
  color: "white",
  border: "none",
  borderRadius: "0.5rem",
  padding: "0.625rem 1.25rem",
  fontSize: "0.9375rem",
  fontWeight: 600,
  cursor: "pointer",
};

const tokenStyle: React.CSSProperties = {
  fontFamily: "monospace",
  fontSize: "0.8125rem",
  background: "#f3f4f6",
  padding: "0.5rem 0.75rem",
  borderRadius: "0.375rem",
  wordBreak: "break-all",
  margin: "1rem 0",
};

const errorStyle: React.CSSProperties = {
  color: "#dc2626",
  fontSize: "0.875rem",
};

export default function LoginPage() {
  const {
    isLoading,
    isAuthenticated,
    error,
    user,
    loginWithRedirect,
    logout,
    getAccessTokenSilently,
  } = useAuth0();
  const [tokenPreview, setTokenPreview] = useState<string | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      setTokenPreview(null);
      return;
    }
    getAccessTokenSilently()
      .then((token) => setTokenPreview(`${token.slice(0, 24)}...`))
      .catch((err: Error) => setTokenError(err.message));
  }, [isAuthenticated, getAccessTokenSilently]);

  if (isLoading) {
    return (
      <div style={pageStyle}>
        <p>Chargement…</p>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <div style={cardStyle}>
        <h1 style={titleStyle}>Authentification Auth0</h1>
        <p style={subtitleStyle}>
          Phase 10.4.2 — vérifie la connexion et l'obtention d'un access
          token ; la résolution du profil côté backend arrive en 10.4.4.
        </p>

        {error && <p style={errorStyle}>{error.message}</p>}

        {!isAuthenticated ? (
          <button style={buttonStyle} onClick={() => loginWithRedirect()}>
            Se connecter
          </button>
        ) : (
          <>
            <p>Connecté en tant que {user?.email ?? user?.sub}</p>
            {tokenPreview && (
              <p style={tokenStyle}>Access token : {tokenPreview}</p>
            )}
            {tokenError && <p style={errorStyle}>{tokenError}</p>}
            <button
              style={buttonStyle}
              onClick={() =>
                logout({ logoutParams: { returnTo: window.location.origin } })
              }
            >
              Se déconnecter
            </button>
          </>
        )}
      </div>
    </div>
  );
}
