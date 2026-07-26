import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SkillsInput from "./skills_input";

describe("SkillsInput", () => {
  it("displays existing skills", () => {
    render(<SkillsInput value={["React", "TypeScript"]} onChange={vi.fn()} />);
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
  });

  it("adds a skill on Add button click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SkillsInput value={["React"]} onChange={onChange} />);

    await user.type(screen.getByLabelText("New skill"), "Python");
    await user.click(screen.getByText("Add"));

    expect(onChange).toHaveBeenCalledWith(["React", "Python"]);
  });

  it("adds a skill on Enter key", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SkillsInput value={[]} onChange={onChange} />);

    await user.type(screen.getByLabelText("New skill"), "FastAPI{Enter}");

    expect(onChange).toHaveBeenCalledWith(["FastAPI"]);
  });

  it("removes a skill via × button", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SkillsInput value={["React", "Python"]} onChange={onChange} />);

    await user.click(screen.getByLabelText("Remove React"));

    expect(onChange).toHaveBeenCalledWith(["Python"]);
  });

  it("does not add a duplicate skill", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SkillsInput value={["React"]} onChange={onChange} />);

    await user.type(screen.getByLabelText("New skill"), "React");
    await user.click(screen.getByText("Add"));

    expect(onChange).not.toHaveBeenCalled();
  });

  it("clears the input after adding", async () => {
    const user = userEvent.setup();
    render(<SkillsInput value={[]} onChange={vi.fn()} />);

    const input = screen.getByLabelText("New skill");
    await user.type(input, "Python");
    await user.click(screen.getByText("Add"));

    expect(input).toHaveValue("");
  });

  it("shows the error message", () => {
    render(
      <SkillsInput
        value={[]}
        onChange={vi.fn()}
        error="At least one skill is required"
      />
    );
    expect(
      screen.getByText("At least one skill is required")
    ).toBeInTheDocument();
  });
});
