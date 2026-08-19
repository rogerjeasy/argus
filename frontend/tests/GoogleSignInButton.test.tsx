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

  it("swaps to loadingText while loading, when one is given", () => {
    render(
      <GoogleSignInButton loading loadingText="Signing in…">
        Continue with Google
      </GoogleSignInButton>
    );
    expect(screen.getByRole("button", { name: "Signing in…" })).toBeInTheDocument();
    expect(screen.queryByText("Continue with Google")).not.toBeInTheDocument();
  });

  it("shows the real label again once loading finishes", () => {
    const { rerender } = render(
      <GoogleSignInButton loading loadingText="Signing in…">
        Continue with Google
      </GoogleSignInButton>
    );
    rerender(
      <GoogleSignInButton loadingText="Signing in…">Continue with Google</GoogleSignInButton>
    );
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeInTheDocument();
  });
});
