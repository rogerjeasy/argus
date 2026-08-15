import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AuthShell } from "../components/auth/AuthShell";

describe("AuthShell", () => {
  it("renders its children inside the content panel", () => {
    render(
      <AuthShell>
        <div data-testid="form-slot">form goes here</div>
      </AuthShell>
    );
    expect(screen.getByTestId("form-slot")).toBeInTheDocument();
  });

  it("renders the brand panel, hidden below the lg breakpoint", () => {
    render(
      <AuthShell>
        <div>content</div>
      </AuthShell>
    );
    const brandCopy = screen.getByText(/seeing-eye copilot/i);
    expect(brandCopy.closest("div.hidden")).not.toBeNull();
  });
});
