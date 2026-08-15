import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarketingFooter } from "../components/marketing/MarketingFooter";

describe("MarketingFooter", () => {
  it("renders the current year in the copyright line, with no dead links", () => {
    render(<MarketingFooter />);
    expect(screen.getByText(`© ${new Date().getFullYear()} Argus.`)).toBeInTheDocument();

    const links = screen.getAllByRole("link");
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link.getAttribute("href")).not.toBe("#");
      expect(link.getAttribute("href")).not.toBeNull();
    }
  });
});
