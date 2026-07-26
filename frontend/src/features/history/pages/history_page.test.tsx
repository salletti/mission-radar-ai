import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HistoryPage from "./history_page";
import { useHistory } from "../hooks/use_history";
import type { ActivityHistoryPage } from "../types/activity_event";

vi.mock("../hooks/use_history");

const _NOW = "2026-06-27T10:30:00Z";

function makeEvent(id: string, overrides = {}) {
  return {
    type: "MISSION_MATCH" as const,
    occurred_at: _NOW,
    title: `Mission ${id}`,
    description: `Description ${id}`,
    mission_match_id: id,
    score: 85,
    ...overrides,
  };
}

function makePage(overrides: Partial<ActivityHistoryPage> = {}): ActivityHistoryPage {
  return {
    items: [makeEvent("m-1")],
    total: 1,
    limit: 20,
    offset: 0,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <HistoryPage />
    </MemoryRouter>
  );
}

describe("HistoryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page title", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makePage(),
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    expect(screen.getByRole("heading", { name: "Historique" })).toBeInTheDocument();
  });

  it("renders loading state", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    expect(screen.getByText("Chargement…")).toBeInTheDocument();
  });

  it("renders error state", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    expect(screen.getByText(/erreur est survenue/i)).toBeInTheDocument();
  });

  it("renders empty state when no items", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makePage({ items: [], total: 0 }),
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    expect(screen.getByText(/Aucune activité/i)).toBeInTheDocument();
  });

  it("renders activity items", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makePage({
        items: [makeEvent("m-1"), makeEvent("m-2")],
        total: 2,
      }),
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    expect(screen.getByText("Mission m-1")).toBeInTheDocument();
    expect(screen.getByText("Mission m-2")).toBeInTheDocument();
  });

  it("renders score badge for each item", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makePage(),
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("renders link to mission detail", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makePage(),
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    const link = screen.getByRole("link", { name: "Mission m-1" });
    expect(link).toHaveAttribute("href", "/missions/m-1");
  });

  it("hides pagination when items is empty", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makePage({ items: [], total: 0 }),
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    expect(screen.queryByText("← Précédent")).not.toBeInTheDocument();
  });

  it("disables Précédent on first page", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makePage({ total: 25 }),
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    expect(screen.getByText("← Précédent")).toBeDisabled();
  });

  it("disables Suivant on last page", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makePage({ total: 1 }),
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    expect(screen.getByText("Suivant →")).toBeDisabled();
  });

  it("increments page when Suivant is clicked", () => {
    vi.mocked(useHistory).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makePage({ total: 25 }),
    } as unknown as ReturnType<typeof useHistory>);

    renderPage();
    fireEvent.click(screen.getByText("Suivant →"));

    expect(vi.mocked(useHistory)).toHaveBeenLastCalledWith(1);
  });
});
