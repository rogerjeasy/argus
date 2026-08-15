import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ArchitectureSection } from "../components/marketing/ArchitectureSection";

describe("ArchitectureSection", () => {
  it("renders the headline and the Grounding/Guardrail trust-boundary node", () => {
    render(<ArchitectureSection />);
    expect(screen.getByRole("heading", { name: /eleven core agents/i })).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /grounding and guardrail trust boundary/i })
    ).toBeInTheDocument();
    expect(screen.getByText("GROUNDING")).toBeInTheDocument();
    expect(screen.getByText("+ GUARDRAIL")).toBeInTheDocument();
  });

  it("shows all six task domains tagged with their tier", () => {
    render(<ArchitectureSection />);
    expect(screen.getByText(/Transit Navigation · Tier 1/)).toBeInTheDocument();
    expect(screen.getByText(/Document & Currency Reading · Tier 3/)).toBeInTheDocument();
  });
});
