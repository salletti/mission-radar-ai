import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MissingSkillsCard from "./missing_skills_card";

describe("MissingSkillsCard", () => {
  it("renders each missing skill", () => {
    render(<MissingSkillsCard skills={["kubernetes", "terraform"]} />);
    expect(screen.getByText("kubernetes")).toBeInTheDocument();
    expect(screen.getByText("terraform")).toBeInTheDocument();
  });

  it("displays the section title", () => {
    render(<MissingSkillsCard skills={["kubernetes"]} />);
    expect(screen.getByText("Compétences manquantes")).toBeInTheDocument();
  });

  it("renders nothing when the list is empty", () => {
    const { container } = render(<MissingSkillsCard skills={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
