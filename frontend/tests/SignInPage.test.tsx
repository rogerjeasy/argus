import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SignInPage from "../app/sign-in/page";
import { useAuth } from "../lib/auth/AuthProvider";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("../lib/auth/AuthProvider", () => ({
  useAuth: vi.fn(),
}));

describe("SignInPage", () => {
  it("renders the sign-in heading and a link to sign-up", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      loading: false,
      signInWithGoogle: vi.fn(),
      signInWithEmail: vi.fn(),
      signUpWithEmail: vi.fn(),
      signOutUser: vi.fn(),
    });

    render(<SignInPage />);

    expect(screen.getByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create an account" })).toHaveAttribute("href", "/sign-up");
  });

  it("redirects to /app when the user is already signed in", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { uid: "user-1" },
      loading: false,
      signInWithGoogle: vi.fn(),
      signInWithEmail: vi.fn(),
      signUpWithEmail: vi.fn(),
      signOutUser: vi.fn(),
    } as never);

    render(<SignInPage />);

    expect(replace).toHaveBeenCalledWith("/app");
  });
});
