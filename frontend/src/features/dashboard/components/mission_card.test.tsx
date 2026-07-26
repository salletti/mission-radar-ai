import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import MissionCard from "./mission_card";
import type { TodayMission } from "../types/mission";

const baseMission: TodayMission = {
  mission_match_id: "abc-123",
  analyzed_post_id: "ap-1",
  raw_post_id: "rp-1",
  author_name: "Alice Martin",
  content_excerpt: "Nous recherchons un développeur React senior pour une mission freelance.",
  post_url: "https://linkedin.com/posts/alice",
  detected_stack: ["React", "TypeScript", "Node.js"],
  detected_contract_type: "freelance",
  detected_remote_mode: "full_remote",
  global_score: 0.85,
  score_details: { semantic: 0.9, contract: 0.8, tjm: 0.75, remote: 1.0 },
  detected_tjm: 650,
  title: "Développeur React Senior",
  company: "Acme Corp",
  location: "Paris",
};

function renderCard(mission: TodayMission = baseMission) {
  return render(
    <MemoryRouter>
      <ul>
        <MissionCard mission={mission} />
      </ul>
    </MemoryRouter>
  );
}

describe("MissionCard", () => {
  it("renders the author name", () => {
    renderCard();
    expect(screen.getByText("Alice Martin")).toBeInTheDocument();
  });

  it("renders the content excerpt", () => {
    renderCard();
    expect(
      screen.getByText(/Nous recherchons un développeur React/)
    ).toBeInTheDocument();
  });

  it("renders all stack badges", () => {
    renderCard();
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("Node.js")).toBeInTheDocument();
  });

  it("renders global_score as a percentage label", () => {
    renderCard();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("renders detected_contract_type and detected_remote_mode in the meta row", () => {
    renderCard();
    expect(screen.getByText(/freelance · full_remote/)).toBeInTheDocument();
  });

  it("renders a link to the mission detail page", () => {
    renderCard();
    const link = screen.getByRole("link", { name: "Voir le détail" });
    expect(link).toHaveAttribute("href", "/missions/abc-123");
  });

  it("renders gracefully when optional fields are null", () => {
    const mission: TodayMission = {
      ...baseMission,
      title: null,
      company: null,
      detected_tjm: null,
    };
    renderCard(mission);
    expect(screen.getByText("Alice Martin")).toBeInTheDocument();
  });

  it("renders without stack badges when detected_stack is empty", () => {
    const mission: TodayMission = { ...baseMission, detected_stack: [] };
    renderCard(mission);
    expect(screen.queryByText("React")).not.toBeInTheDocument();
  });
});
