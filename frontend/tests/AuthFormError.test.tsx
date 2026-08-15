import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AuthFormError } from "../components/auth/AuthFormError";

describe("AuthFormError", () => {
  it("renders nothing when there is no message", () => {
    const { container } = render(<AuthFormError message={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the message inside an alert region when present", () => {
    render(<AuthFormError message="That email or password doesn't look right. Please try again." />);
    expect(screen.getByRole("alert").textContent).toContain("doesn't look right");
  });
});
