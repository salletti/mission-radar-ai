import { useAuth0 } from "@auth0/auth0-react";
import { Link, Outlet, useLocation } from "react-router-dom";

const layoutStyle: React.CSSProperties = {
  display: "flex",
  minHeight: "100vh",
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  background: "#f9fafb",
};

const sidebarStyle: React.CSSProperties = {
  width: "220px",
  flexShrink: 0,
  background: "white",
  borderRight: "1px solid #e5e7eb",
  display: "flex",
  flexDirection: "column",
  padding: "1.5rem 0",
};

const sidebarTitleStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  fontWeight: 700,
  color: "#9ca3af",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  padding: "0 1.25rem",
  marginBottom: "0.75rem",
};

const navStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.25rem",
  padding: "0 0.75rem",
};

const mainContainerStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  flexDirection: "column",
  overflow: "auto",
};

const headerStyle: React.CSSProperties = {
  background: "white",
  borderBottom: "1px solid #e5e7eb",
  padding: "1rem 2rem",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const headerTitleStyle: React.CSSProperties = {
  fontSize: "1.125rem",
  fontWeight: 700,
  color: "#111827",
  margin: 0,
};

const logoutButtonStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #e5e7eb",
  borderRadius: "0.375rem",
  padding: "0.375rem 0.75rem",
  fontSize: "0.8125rem",
  color: "#6b7280",
  cursor: "pointer",
};

const mainStyle: React.CSSProperties = {
  flex: 1,
  padding: "2rem",
};

const navLinks = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/history", label: "Historique" },
];

function NavLink({ to, label }: { to: string; label: string }) {
  const { pathname } = useLocation();
  const isActive = pathname === to;

  const linkStyle: React.CSSProperties = {
    display: "block",
    padding: "0.5rem 0.75rem",
    borderRadius: "0.375rem",
    fontSize: "0.875rem",
    fontWeight: isActive ? 600 : 400,
    color: isActive ? "#4f46e5" : "#6b7280",
    background: isActive ? "#ede9fe" : "transparent",
    textDecoration: "none",
  };

  return (
    <Link to={to} style={linkStyle}>
      {label}
    </Link>
  );
}

export default function DashboardLayout() {
  const { isAuthenticated, logout } = useAuth0();

  return (
    <div style={layoutStyle}>
      <aside style={sidebarStyle}>
        <p style={sidebarTitleStyle}>Navigation</p>
        <nav style={navStyle}>
          {navLinks.map((link) => (
            <NavLink key={link.to} to={link.to} label={link.label} />
          ))}
        </nav>
      </aside>

      <div style={mainContainerStyle}>
        <header style={headerStyle}>
          <h1 style={headerTitleStyle}>Mission Radar AI</h1>
          {isAuthenticated && (
            <button
              style={logoutButtonStyle}
              onClick={() =>
                logout({ logoutParams: { returnTo: window.location.origin } })
              }
            >
              Se déconnecter
            </button>
          )}
        </header>
        <main style={mainStyle}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
