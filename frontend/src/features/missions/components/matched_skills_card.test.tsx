import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MatchedSkillsCard from "./matched_skills_card";

describe("MatchedSkillsCard", () => {
  it("renders each matched skill with a checkmark", () => {
    render(<MatchedSkillsCard skills={["python", "fastapi", "docker"]} />);
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("fastapi")).toBeInTheDocument();
    expect(screen.getByText("docker")).toBeInTheDocument();
    expect(screen.getAllByText("✓")).toHaveLength(3);
  });

  it("displays the section title", () => {
    render(<MatchedSkillsCard skills={["python"]} />);
    expect(screen.getByText("Compétences matchées")).toBeInTheDocument();
  });

  it("renders nothing when the list is empty", () => {
    const { container } = render(<MatchedSkillsCard skills={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
