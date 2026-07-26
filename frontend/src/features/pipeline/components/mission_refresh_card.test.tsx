import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MissionRefreshCard from "./mission_refresh_card";
import { useMissionRefresh } from "../hooks/use_mission_refresh";
import type { PipelineRun } from "../types/pipeline_run";

vi.mock("../hooks/use_mission_refresh");

const mockRun = (
  overrides: Partial<PipelineRun> = {}
): PipelineRun => ({
  id: "run-1",
  user_id: "user-1",
  pipeline_type: "mission_refresh",
  trigger_type: "user",
  status: "running",
  current_step: "collect",
  progress: 0.33,
  started_at: "2026-06-28T11:00:00Z",
  finished_at: null,
  error_message: null,
  created_at: "2026-06-28T11:00:00Z",
  ...overrides,
});

const defaultRefreshState = {
  pipelineRun: null,
  lastSyncAt: null,
  isPolling: false,
  isTimedOut: false,
  isStarting: false,
  startError: null,
  pollingError: null,
  startRefresh: vi.fn(),
};

function renderCard() {
  return render(<MissionRefreshCard />);
}

describe("MissionRefreshCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders 'Jamais' when no prior run and no lastSyncAt", () => {
    vi.mocked(useMissionRefresh).mockReturnValue({ ...defaultRefreshState });
    renderCard();
    expect(screen.getByText("Jamais")).toBeInTheDocument();
  });

  it("button is enabled and calls startRefresh on click", async () => {
    const startRefresh = vi.fn();
    vi.mocked(useMissionRefresh).mockReturnValue({
      ...defaultRefreshState,
      startRefresh,
    });

    renderCard();
    const btn = screen.getByRole("button", { name: /mettre à jour/i });
    expect(btn).not.toBeDisabled();

    await userEvent.click(btn);
    expect(startRefresh).toHaveBeenCalledOnce();
  });

  it("button is disabled when isPolling is true", () => {
    vi.mocked(useMissionRefresh).mockReturnValue({
      ...defaultRefreshState,
      pipelineRun: mockRun(),
      isPolling: true,
    });

    renderCard();
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("button is disabled and shows 'Démarrage...' when isStarting is true", () => {
    vi.mocked(useMissionRefresh).mockReturnValue({
      ...defaultRefreshState,
      isStarting: true,
    });

    renderCard();
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent("Démarrage...");
  });

  it("shows step indicators when pipeline is running", () => {
    vi.mocked(useMissionRefresh).mockReturnValue({
      ...defaultRefreshState,
      pipelineRun: mockRun({ status: "running", current_step: "analyze", progress: 0.66 }),
      isPolling: true,
    });

    renderCard();
    expect(screen.getByText(/Collect/)).toBeInTheDocument();
    expect(screen.getByText(/Analyze/)).toBeInTheDocument();
    expect(screen.getByText(/Match/)).toBeInTheDocument();
  });

  it("shows progress percentage when polling", () => {
    vi.mocked(useMissionRefresh).mockReturnValue({
      ...defaultRefreshState,
      pipelineRun: mockRun({ status: "running", current_step: "analyze", progress: 0.66 }),
      isPolling: true,
    });

    renderCard();
    expect(screen.getByText("66%")).toBeInTheDocument();
  });

  it("shows formatted last sync date when completed", () => {
    const finishedAt = "2026-06-28T10:30:00Z";
    vi.mocked(useMissionRefresh).mockReturnValue({
      ...defaultRefreshState,
      pipelineRun: mockRun({
        status: "completed",
        current_step: "done",
        progress: 1.0,
        finished_at: finishedAt,
      }),
      isPolling: false,
    });

    renderCard();
    expect(screen.getByText(/Pipeline terminé/)).toBeInTheDocument();
    const formatted = new Date(finishedAt).toLocaleString("fr-FR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
    expect(screen.getByText(formatted)).toBeInTheDocument();
  });

  it("shows error message when pipeline has failed", () => {
    vi.mocked(useMissionRefresh).mockReturnValue({
      ...defaultRefreshState,
      pipelineRun: mockRun({
        status: "failed",
        error_message: "Connexion Apify impossible",
      }),
      isPolling: false,
    });

    renderCard();
    expect(
      screen.getByRole("alert")
    ).toHaveTextContent(/Connexion Apify impossible/);
  });

  it("shows startError when mutation fails", () => {
    vi.mocked(useMissionRefresh).mockReturnValue({
      ...defaultRefreshState,
      startError: new Error("Un pipeline est déjà en cours"),
    });

    renderCard();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Un pipeline est déjà en cours"
    );
  });

  it("shows lastSyncAt from localStorage when no current pipeline run", () => {
    vi.mocked(useMissionRefresh).mockReturnValue({
      ...defaultRefreshState,
      lastSyncAt: "2026-06-27T08:00:00Z",
    });

    renderCard();
    const formatted = new Date("2026-06-27T08:00:00Z").toLocaleString("fr-FR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
    expect(screen.getByText(formatted)).toBeInTheDocument();
  });
});
