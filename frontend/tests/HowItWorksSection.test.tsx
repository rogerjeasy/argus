import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HowItWorksSection } from "../components/marketing/HowItWorksSection";

describe("HowItWorksSection", () => {
  it("renders all five loop stages, in order", () => {
    render(<HowItWorksSection />);
    const headings = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(headings).toEqual(["Goal", "Perceive", "Plan", "Act", "Verify / Replan"]);
  });
});
