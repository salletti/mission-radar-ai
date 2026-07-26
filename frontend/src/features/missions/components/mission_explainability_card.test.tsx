import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MissionExplainabilityCard from "./mission_explainability_card";
import type { Explanation } from "../types/mission_detail";

const baseExplanation: Explanation = {
  score_breakdown: { skills: null, experience: null, location: null, contract: 1.0, daily_rate: 0.7 },
  matching_reasons: [],
  warnings: [],
  strong_points: [],
  missing_skills: [],
  recommendations: [],
};

describe("MissionExplainabilityCard", () => {
  it("renders matching_reasons", () => {
    const explanation: Explanation = {
      ...baseExplanation,
      matching_reasons: [
        "Votre expérience python correspond à la stack demandée.",
        "Votre préférence de contrat (freelance) correspond au type proposé.",
      ],
    };
    render(<MissionExplainabilityCard explanation={explanation} />);
    expect(
      screen.getByText("Votre expérience python correspond à la stack demandée.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Votre préférence de contrat (freelance) correspond au type proposé.")
    ).toBeInTheDocument();
  });

  it("displays the section title", () => {
    const explanation: Explanation = {
      ...baseExplanation,
      matching_reasons: ["Votre expérience python correspond."],
    };
    render(<MissionExplainabilityCard explanation={explanation} />);
    expect(
      screen.getByText("Pourquoi cette mission vous est proposée")
    ).toBeInTheDocument();
  });

  it("renders nothing when all lists are empty", () => {
    const { container } = render(<MissionExplainabilityCard explanation={baseExplanation} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders strong_points section when present", () => {
    const explanation: Explanation = {
      ...baseExplanation,
      strong_points: ["python", "fastapi"],
    };
    render(<MissionExplainabilityCard explanation={explanation} />);
    expect(screen.getByText("Points forts")).toBeInTheDocument();
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("fastapi")).toBeInTheDocument();
  });

  it("renders warnings section when present", () => {
    const explanation: Explanation = {
      ...baseExplanation,
      warnings: ["TJM non détecté dans cette annonce."],
    };
    render(<MissionExplainabilityCard explanation={explanation} />);
    expect(screen.getByText("Points d'attention")).toBeInTheDocument();
    expect(screen.getByText("TJM non détecté dans cette annonce.")).toBeInTheDocument();
  });

  it("renders recommendations section when present", () => {
    const explanation: Explanation = {
      ...baseExplanation,
      recommendations: ["Mettez à jour votre profil avec Kubernetes."],
    };
    render(<MissionExplainabilityCard explanation={explanation} />);
    expect(screen.getByText("Recommandations")).toBeInTheDocument();
  });
});
