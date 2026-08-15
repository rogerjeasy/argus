// frontend/tests/TrustSection.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TrustSection } from "../components/marketing/TrustSection";

describe("TrustSection", () => {
  it("renders all four trust points", () => {
    render(<TrustSection />);
    expect(screen.getByRole("heading", { name: /no raw video/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /tiered autonomy/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /inbound content is untrusted/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /encrypted at rest/i })).toBeInTheDocument();
  });
});
