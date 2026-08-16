import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GuardrailStatus } from "@/components/GuardrailStatus";

describe("GuardrailStatus", () => {
  it("renders approved with a success tone", () => {
    render(<GuardrailStatus decision="approved" />);
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("renders requires_confirmation with a warning tone", () => {
    render(<GuardrailStatus decision="requires_confirmation" />);
    expect(screen.getByText("Needs your confirmation")).toBeInTheDocument();
  });

  it("renders denied with a destructive tone", () => {
    render(<GuardrailStatus decision="denied" />);
    expect(screen.getByText("Denied")).toBeInTheDocument();
  });
});
