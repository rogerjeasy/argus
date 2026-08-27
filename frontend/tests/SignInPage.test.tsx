import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

    expect(replace).toHaveBeenCalledWith("/dashboard");
  });

  it("shows a mapped error when Google sign-in fails", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      loading: false,
      signInWithGoogle: vi.fn().mockRejectedValue({ code: "auth/too-many-requests" }),
      signInWithEmail: vi.fn(),
      signUpWithEmail: vi.fn(),
      signOutUser: vi.fn(),
    });

    render(<SignInPage />);

    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Too many attempts. Please wait a moment and try again.")
    );
  });
});
