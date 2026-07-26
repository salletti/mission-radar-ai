import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import KpiCard from "./kpi_card";

describe("KpiCard", () => {
  it("renders the label", () => {
    render(<KpiCard label="Missions totales" value={42} />);
    expect(screen.getByText("Missions totales")).toBeInTheDocument();
  });

  it("renders a numeric value", () => {
    render(<KpiCard label="Score moyen" value={89} />);
    expect(screen.getByText("89")).toBeInTheDocument();
  });

  it("renders a string value", () => {
    render(<KpiCard label="Dernière sync" value="30/06/2026" />);
    expect(screen.getByText("30/06/2026")).toBeInTheDocument();
  });

  it("renders the optional description", () => {
    render(<KpiCard label="Label" value={10} description="sur 20 missions" />);
    expect(screen.getByText("sur 20 missions")).toBeInTheDocument();
  });

  it("hides the description in loading state", () => {
    render(<KpiCard label="Label" value={10} description="desc" loading />);
    expect(screen.queryByText("desc")).not.toBeInTheDocument();
  });

  it("does not render the value in loading state", () => {
    render(<KpiCard label="Label" value={42} loading />);
    expect(screen.queryByText("42")).not.toBeInTheDocument();
  });
});
