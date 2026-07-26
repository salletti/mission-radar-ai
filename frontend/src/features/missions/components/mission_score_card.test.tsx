import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MissionScoreCard from "./mission_score_card";
import type { MissionDetail } from "../types/mission_detail";

const mockMission: MissionDetail = {
  mission_match_id: "m-1",
  analyzed_post_id: "ap-1",
  raw_post_id: "rp-1",
  author_name: "Alice",
  content_excerpt: "Mission Python",
  post_url: "https://linkedin.com/posts/1",
  detected_stack: ["python"],
  detected_contract_type: "freelance",
  detected_remote_mode: "full_remote",
  global_score: 0.92,
  score_details: { semantic: 0.9, contract: 1.0, tjm: 0.75, remote: 1.0 },
  detected_tjm: 700,
  title: "Senior Python Engineer",
  company: "Acme",
  location: "Paris",
  author_url: "https://linkedin.com/in/alice",
  content: "Full content here",
  published_at: "2026-06-01T10:00:00Z",
  summary: "Summary here",
  seniority: null,
  matched_at: "2026-06-28T10:00:00Z",
  matched_skills: ["python"],
  missing_skills: [],
  explainability_hints: [],
};

describe("MissionScoreCard", () => {
  it("displays the global score as a percentage", () => {
    render(<MissionScoreCard mission={mockMission} />);
    expect(screen.getByText("92%")).toBeInTheDocument();
  });

  it("displays the 'Score de matching' label", () => {
    render(<MissionScoreCard mission={mockMission} />);
    expect(screen.getByText("Score de matching")).toBeInTheDocument();
  });

  it("displays the four sub-score labels", () => {
    render(<MissionScoreCard mission={mockMission} />);
    expect(screen.getByText(/Correspondance sémantique/)).toBeInTheDocument();
    expect(screen.getByText(/Type de contrat/)).toBeInTheDocument();
    expect(screen.getByText(/Télétravail/)).toBeInTheDocument();
    expect(screen.getByText(/TJM/)).toBeInTheDocument();
  });

  it("displays sub-score percentage values", () => {
    render(<MissionScoreCard mission={mockMission} />);
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
  });
});
