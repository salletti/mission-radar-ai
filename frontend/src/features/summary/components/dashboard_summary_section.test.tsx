import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardSummarySection from "./dashboard_summary_section";
import { useDashboardSummary } from "../hooks/use_dashboard_summary";
import type { DashboardSummary } from "../types/dashboard_summary";

vi.mock("../hooks/use_dashboard_summary");

const mockSummary: DashboardSummary = {
  kpis: {
    total_missions: 42,
    new_today: 8,
    average_score: 89,
    last_refresh: "2026-06-30T07:00:00Z",
    pipeline_status: "completed",
  },
  health: {
    status: "OK",
    last_pipeline_duration_seconds: 34.0,
  },
};

function renderSection() {
  return render(<DashboardSummarySection />);
}

describe("DashboardSummarySection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders KPI labels when data is loaded", () => {
    vi.mocked(useDashboardSummary).mockReturnValue({
      data: mockSummary,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDashboardSummary>);

    renderSection();
    expect(screen.getByText("Missions totales")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Nouvelles aujourd'hui")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("Score moyen")).toBeInTheDocument();
    expect(screen.getByText("89%")).toBeInTheDocument();
  });

  it("renders health status OK in green", () => {
    vi.mocked(useDashboardSummary).mockReturnValue({
      data: mockSummary,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDashboardSummary>);

    renderSection();
    expect(screen.getByText("Santé système")).toBeInTheDocument();
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  it("renders health status DEGRADED for failed pipeline", () => {
    vi.mocked(useDashboardSummary).mockReturnValue({
      data: {
        ...mockSummary,
        health: { status: "DEGRADED", last_pipeline_duration_seconds: null },
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDashboardSummary>);

    renderSection();
    expect(screen.getByText("DEGRADED")).toBeInTheDocument();
  });

  it("renders pipeline status label in French", () => {
    vi.mocked(useDashboardSummary).mockReturnValue({
      data: mockSummary,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDashboardSummary>);

    renderSection();
    expect(screen.getByText("Terminé")).toBeInTheDocument();
  });

  it("renders duration when available", () => {
    vi.mocked(useDashboardSummary).mockReturnValue({
      data: mockSummary,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDashboardSummary>);

    renderSection();
    expect(screen.getByText("Durée : 34s")).toBeInTheDocument();
  });

  it("shows loading state (no values)", () => {
    vi.mocked(useDashboardSummary).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useDashboardSummary>);

    renderSection();
    expect(screen.queryByText("42")).not.toBeInTheDocument();
    expect(screen.getByText("Missions totales")).toBeInTheDocument();
  });

  it("shows error message on failure", () => {
    vi.mocked(useDashboardSummary).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useDashboardSummary>);

    renderSection();
    expect(
      screen.getByText(/Impossible de charger le résumé/)
    ).toBeInTheDocument();
  });

  it("renders 'Jamais' when last_refresh is null", () => {
    vi.mocked(useDashboardSummary).mockReturnValue({
      data: {
        ...mockSummary,
        kpis: { ...mockSummary.kpis, last_refresh: null, pipeline_status: null },
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDashboardSummary>);

    renderSection();
    expect(screen.getByText("Jamais")).toBeInTheDocument();
  });

  it("renders UNKNOWN health in neutral color", () => {
    vi.mocked(useDashboardSummary).mockReturnValue({
      data: {
        ...mockSummary,
        health: { status: "UNKNOWN", last_pipeline_duration_seconds: null },
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDashboardSummary>);

    renderSection();
    expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
  });
});
