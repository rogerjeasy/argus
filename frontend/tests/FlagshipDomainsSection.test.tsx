// frontend/tests/FlagshipDomainsSection.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FlagshipDomainsSection } from "../components/marketing/FlagshipDomainsSection";

describe("FlagshipDomainsSection", () => {
  it("renders both flagship domains with their proof statements", () => {
    render(<FlagshipDomainsSection />);
    expect(screen.getByRole("heading", { name: /platform changes at the last minute/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /a real phone call/i })).toBeInTheDocument();
    expect(screen.getAllByText("Tier 1 · proven live")).toHaveLength(2);
  });

  it("shows the confirmation gate and reported outcome for the Personal Admin flow", () => {
    render(<FlagshipDomainsSection />);
    expect(screen.getByText("Call the pharmacy to confirm refill status?")).toBeInTheDocument();
    expect(screen.getByText(/refill confirmed, ready tomorrow/i)).toBeInTheDocument();
  });
});
