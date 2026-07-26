import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UserProfileContext } from "@/context/user_profile_context";
import OnboardingPage from "./onboarding_page";
import * as api from "../api/onboarding_api";

vi.mock("../api/onboarding_api");

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <UserProfileContext.Provider
      value={{
        profileId: null,
        userEmail: null,
        isLoading: false,
        needsOnboarding: true,
        refetch: async () => {},
      }}
    >
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <OnboardingPage />
        </MemoryRouter>
      </QueryClientProvider>
    </UserProfileContext.Provider>
  );
}

const mockDraft = {
  cv_profile: {
    email: "john@example.com",
    full_name: "John Doe",
    title: "Senior Developer",
    years_experience: 10,
    preferred_contract_type: "freelance",
    target_tjm: 700,
    preferred_remote_mode: "full_remote",
    location: "Paris",
    skills: ["React", "TypeScript", "Python"],
    availability: "2025-06-01T00:00:00",
  },
  cv_raw_text: "John Doe — Senior Developer at Acme Corp...",
};

async function uploadValidCv(user: ReturnType<typeof userEvent.setup>) {
  const file = new File(["pdf"], "cv.pdf", { type: "application/pdf" });
  await user.type(screen.getByLabelText("Email"), "john@example.com");
  await user.upload(screen.getByLabelText("CV (PDF)"), file);
  await user.click(screen.getByText("Analyze CV"));
}

describe("OnboardingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the upload form initially", () => {
    renderPage();
    expect(screen.getByText("Analyze CV")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("CV (PDF)")).toBeInTheDocument();
  });

  it("shows loading step while the mutation is pending", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadCv).mockImplementation(() => new Promise(() => {}));

    renderPage();
    await uploadValidCv(user);

    await waitFor(() => {
      expect(screen.getByText("Analyzing your CV...")).toBeInTheDocument();
    });
  });

  it("shows the review form pre-filled with draft data after upload", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadCv).mockResolvedValue(mockDraft);

    renderPage();
    await uploadValidCv(user);

    await waitFor(() => {
      expect(screen.getByDisplayValue("John Doe")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Senior Developer")).toBeInTheDocument();
      expect(screen.getByDisplayValue("10")).toBeInTheDocument();
      expect(screen.getByDisplayValue("700")).toBeInTheDocument();
    });
  });

  it("displays draft skills as chips in the review step", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadCv).mockResolvedValue(mockDraft);

    renderPage();
    await uploadValidCv(user);

    await waitFor(() => {
      expect(screen.getByText("React")).toBeInTheDocument();
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
      expect(screen.getByText("Python")).toBeInTheDocument();
    });
  });

  it("shows the API error and returns to upload step on failure", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadCv).mockRejectedValue(
      new Error("CV extraction failed")
    );

    renderPage();
    await uploadValidCv(user);

    await waitFor(() => {
      expect(screen.getByText("CV extraction failed")).toBeInTheDocument();
      expect(screen.getByText("Analyze CV")).toBeInTheDocument();
    });
  });

  it("shows Confirm Profile button in the review step", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadCv).mockResolvedValue(mockDraft);

    renderPage();
    await uploadValidCv(user);

    await waitFor(() => {
      expect(screen.getByText("Confirm Profile")).toBeInTheDocument();
    });
  });

  it("navigates to /dashboard after successful profile save", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadCv).mockResolvedValue(mockDraft);
    vi.mocked(api.saveProfile).mockResolvedValue({
      profile_id: "test-uuid-123",
      email: "john@example.com",
      status: "created",
    });

    renderPage();
    await uploadValidCv(user);

    await waitFor(() => {
      expect(screen.getByText("Confirm Profile")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Confirm Profile"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/dashboard");
    });
  });
});
