// frontend/tests/MultimodalSection.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MultimodalSection } from "../components/marketing/MultimodalSection";

describe("MultimodalSection", () => {
  it("renders all three coordinated channels", () => {
    render(<MultimodalSection />);
    expect(screen.getByRole("heading", { name: /voice, with barge-in/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /haptic compass/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /audio earcons/i })).toBeInTheDocument();
  });
});
