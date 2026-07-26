import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MissionDetailPage from "./mission_detail_page";
import { useMission } from "../hooks/use_mission";
import type { MissionDetail } from "../types/mission_detail";

vi.mock("../hooks/use_mission");

const mockDetail: MissionDetail = {
  mission_match_id: "m-1",
  analyzed_post_id: "ap-1",
  raw_post_id: "rp-1",
  author_name: "Alice Martin",
  content_excerpt: "Mission Python FastAPI",
  post_url: "https://linkedin.com/posts/1",
  detected_stack: ["python", "fastapi", "docker"],
  detected_contract_type: "freelance",
  detected_remote_mode: "full_remote",
  global_score: 0.88,
  score_details: { semantic: 0.9, contract: 1.0, tjm: 0.75, remote: 1.0 },
  detected_tjm: 700,
  title: "Senior Python Engineer",
  company: "Acme Corp",
  location: "Paris",
  author_url: "https://linkedin.com/in/alice",
  content: "Mission Python FastAPI full remote 700€/j #freelance.\nExperience requise : 5 ans.",
  published_at: "2026-06-01T10:00:00Z",
  summary: "Mission Python full remote 700€/j.",
  seniority: "senior",
  matched_at: "2026-06-28T10:00:00Z",
  matched_skills: ["python", "fastapi"],
  missing_skills: ["kubernetes"],
  explanation: {
    score_breakdown: { skills: null, experience: null, location: null, contract: 1.0, daily_rate: 0.75 },
    matching_reasons: [
      "Votre expérience python correspond à la stack demandée.",
      "Votre préférence de contrat (freelance) correspond au type proposé.",
    ],
    warnings: [],
    strong_points: ["python", "fastapi"],
    missing_skills: ["kubernetes"],
    recommendations: [],
  },
};

function renderPage(missionId = "m-1") {
  return render(
    <MemoryRouter initialEntries={[`/missions/${missionId}`]}>
      <Routes>
        <Route path="/missions/:id" element={<MissionDetailPage />} />
        <Route path="/dashboard" element={<div>Dashboard</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("MissionDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a loading spinner while data is loading", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
      error: null,
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByLabelText("Loading spinner")).toBeInTheDocument();
  });

  it("renders an error message when the request fails", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
      error: new Error("Mission introuvable"),
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByText("Mission introuvable")).toBeInTheDocument();
  });

  it("renders the mission title when data is loaded", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: false,
      isError: false,
      data: mockDetail,
      error: null,
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByText("Senior Python Engineer")).toBeInTheDocument();
  });

  it("renders the back to dashboard link", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: false,
      isError: false,
      data: mockDetail,
      error: null,
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByText("← Retour au Dashboard")).toBeInTheDocument();
  });

  it("renders the global score percentage", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: false,
      isError: false,
      data: mockDetail,
      error: null,
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByText("88%")).toBeInTheDocument();
  });

  it("renders matched skills section", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: false,
      isError: false,
      data: mockDetail,
      error: null,
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByText("Compétences matchées")).toBeInTheDocument();
    // python appears in both detected stack and matched skills
    expect(screen.getAllByText("python").length).toBeGreaterThan(0);
    expect(screen.getAllByText("fastapi").length).toBeGreaterThan(0);
  });

  it("renders missing skills", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: false,
      isError: false,
      data: mockDetail,
      error: null,
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByText("kubernetes")).toBeInTheDocument();
    expect(screen.getByText("Compétences manquantes")).toBeInTheDocument();
  });

  it("renders the explainability section with hints", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: false,
      isError: false,
      data: mockDetail,
      error: null,
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByText("Pourquoi cette mission vous est proposée")).toBeInTheDocument();
    expect(
      screen.getByText("Votre expérience python correspond à la stack demandée.")
    ).toBeInTheDocument();
  });

  it("renders the mission summary", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: false,
      isError: false,
      data: mockDetail,
      error: null,
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByText("Résumé de l'annonce")).toBeInTheDocument();
    expect(screen.getByText("Mission Python full remote 700€/j.")).toBeInTheDocument();
  });

  it("renders the detected stack chips", () => {
    vi.mocked(useMission).mockReturnValue({
      isLoading: false,
      isError: false,
      data: mockDetail,
      error: null,
    } as unknown as ReturnType<typeof useMission>);

    renderPage();
    expect(screen.getByText("Stack détectée")).toBeInTheDocument();
    expect(screen.getByText("docker")).toBeInTheDocument();
  });
});
