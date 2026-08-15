import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProblemSection } from "../components/marketing/ProblemSection";

describe("ProblemSection", () => {
  it("renders the headline and all three stat callouts", () => {
    render(<ProblemSection />);
    expect(screen.getByRole("heading", { name: /narration is solved/i })).toBeInTheDocument();
    expect(screen.getByText("2.2B")).toBeInTheDocument();
    expect(screen.getByText("43M")).toBeInTheDocument();
    expect(screen.getByText("0 of 5")).toBeInTheDocument();
  });

  it("puts the wide contrast table inside its own horizontally-scrollable container", () => {
    const { container } = render(<ProblemSection />);
    const scrollWrapper = container.querySelector(".overflow-x-auto");
    expect(scrollWrapper).not.toBeNull();
    expect(scrollWrapper?.querySelector("table")).not.toBeNull();
  });
});
