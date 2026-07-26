import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "../pages/login_page";

const useAuth0Mock = vi.fn();

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => useAuth0Mock(),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    useAuth0Mock.mockReset();
  });

  it("shows a loading state", () => {
    useAuth0Mock.mockReturnValue({ isLoading: true });
    render(<LoginPage />);
    expect(screen.getByText("Chargement…")).toBeInTheDocument();
  });

  it("shows a login button when unauthenticated", () => {
    const loginWithRedirect = vi.fn();
    useAuth0Mock.mockReturnValue({
      isLoading: false,
      isAuthenticated: false,
      loginWithRedirect,
      logout: vi.fn(),
      getAccessTokenSilently: vi.fn(),
    });
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: "Se connecter" })).toBeInTheDocument();
  });

  it("calls loginWithRedirect when the login button is clicked", async () => {
    const user = userEvent.setup();
    const loginWithRedirect = vi.fn();
    useAuth0Mock.mockReturnValue({
      isLoading: false,
      isAuthenticated: false,
      loginWithRedirect,
      logout: vi.fn(),
      getAccessTokenSilently: vi.fn(),
    });
    render(<LoginPage />);
    await user.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(loginWithRedirect).toHaveBeenCalled();
  });

  it("shows the authenticated user's email and a token preview", async () => {
    useAuth0Mock.mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
      user: { email: "ada@example.com", sub: "auth0|123" },
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
      getAccessTokenSilently: vi.fn().mockResolvedValue("a".repeat(40)),
    });
    render(<LoginPage />);
    expect(await screen.findByText(/Connecté en tant que ada@example.com/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Access token :/)).toBeInTheDocument();
    });
  });

  it("calls logout when the logout button is clicked", async () => {
    const user = userEvent.setup();
    const logout = vi.fn();
    useAuth0Mock.mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
      user: { email: "ada@example.com", sub: "auth0|123" },
      loginWithRedirect: vi.fn(),
      logout,
      getAccessTokenSilently: vi.fn().mockResolvedValue("token"),
    });
    render(<LoginPage />);
    await user.click(await screen.findByRole("button", { name: "Se déconnecter" }));
    expect(logout).toHaveBeenCalled();
  });
});
