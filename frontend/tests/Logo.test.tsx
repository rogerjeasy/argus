import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Logo } from "../components/marketing/Logo";
import { WatchingRings } from "../components/marketing/WatchingRings";

describe("WatchingRings", () => {
  it("is purely decorative and hidden from assistive tech", () => {
    const { container } = render(<WatchingRings />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });
});

describe("Logo", () => {
  it("renders the wordmark linking to the homepage", () => {
    render(<Logo />);
    const link = screen.getByRole("link", { name: /argus/i });
    expect(link).toHaveAttribute("href", "/");
  });
});
