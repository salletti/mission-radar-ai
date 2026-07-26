import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardPage from "./dashboard_page";
import { useTodayMissions } from "../hooks/use_today_missions";
import type { TodayMission } from "../types/mission";

vi.mock("../hooks/use_today_missions");
vi.mock("@/features/pipeline/components/mission_refresh_card", () => ({
  default: () => <div data-testid="mission-refresh-card" />,
}));
vi.mock("@/features/summary/components/dashboard_summary_section", () => ({
  default: () => <div data-testid="dashboard-summary-section" />,
}));

const mockMission: TodayMission = {
  mission_match_id: "m-1",
  analyzed_post_id: "ap-1",
  raw_post_id: "rp-1",
  author_name: "Alice Martin",
  content_excerpt: "Développeur React senior recherché.",
  post_url: "https://linkedin.com/posts/alice",
  detected_stack: ["React", "TypeScript"],
  detected_contract_type: "freelance",
  detected_remote_mode: "full_remote",
  global_score: 0.82,
  score_details: { semantic: 0.9, contract: 0.8, tjm: 0.7, remote: 0.9 },
  detected_tjm: 650,
  title: null,
  company: null,
  location: null,
};

const mockMission2: TodayMission = {
  ...mockMission,
  mission_match_id: "m-2",
  author_name: "Bob Dupont",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page title 'Missions du jour'", () => {
    vi.mocked(useTodayMissions).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
      error: null,
      fetchStatus: "idle",
    } as unknown as ReturnType<typeof useTodayMissions>);

    renderPage();
    expect(screen.getByRole("heading", { name: "Missions du jour" })).toBeInTheDocument();
  });

  it("renders a loading spinner while isLoading is true", () => {
    vi.mocked(useTodayMissions).mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
      error: null,
      fetchStatus: "fetching",
    } as unknown as ReturnType<typeof useTodayMissions>);

    renderPage();
    expect(screen.getByLabelText("Loading spinner")).toBeInTheDocument();
  });

  it("renders an error message when isError is true", () => {
    vi.mocked(useTodayMissions).mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
      error: new Error("Erreur 500"),
      fetchStatus: "idle",
    } as unknown as ReturnType<typeof useTodayMissions>);

    renderPage();
    expect(screen.getByText("Erreur 500")).toBeInTheDocument();
  });

  it("renders empty state message when data is an empty array", () => {
    vi.mocked(useTodayMissions).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
      error: null,
      fetchStatus: "idle",
    } as unknown as ReturnType<typeof useTodayMissions>);

    renderPage();
    expect(
      screen.getByText(/Aucune mission aujourd'hui/)
    ).toBeInTheDocument();
  });

  it("renders a MissionCard for each mission", () => {
    vi.mocked(useTodayMissions).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [mockMission, mockMission2],
      error: null,
      fetchStatus: "idle",
    } as unknown as ReturnType<typeof useTodayMissions>);

    renderPage();
    expect(screen.getByText("Alice Martin")).toBeInTheDocument();
    expect(screen.getByText("Bob Dupont")).toBeInTheDocument();
  });

  it("renders the MissionRefreshCard", () => {
    vi.mocked(useTodayMissions).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
      error: null,
      fetchStatus: "idle",
    } as unknown as ReturnType<typeof useTodayMissions>);

    renderPage();
    expect(screen.getByTestId("mission-refresh-card")).toBeInTheDocument();
  });

  it("renders both MissionRefreshCard and missions list together", () => {
    vi.mocked(useTodayMissions).mockReturnValue({
      isLoading: false,
      isError: false,
      data: [mockMission],
      error: null,
      fetchStatus: "idle",
    } as unknown as ReturnType<typeof useTodayMissions>);

    renderPage();
    expect(screen.getByTestId("mission-refresh-card")).toBeInTheDocument();
    expect(screen.getByText("Alice Martin")).toBeInTheDocument();
  });
});
