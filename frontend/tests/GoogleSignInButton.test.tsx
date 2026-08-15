import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GoogleSignInButton } from "../components/auth/GoogleSignInButton";

describe("GoogleSignInButton", () => {
  it("renders the Google mark alongside the label", () => {
    render(<GoogleSignInButton>Continue with Google</GoogleSignInButton>);
    const button = screen.getByRole("button", { name: "Continue with Google" });
    expect(button.querySelector("svg")).not.toBeNull();
  });

  it("disables itself while loading", () => {
    render(<GoogleSignInButton loading>Continue with Google</GoogleSignInButton>);
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeDisabled();
  });
});
