import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SignUpPage from "../app/sign-up/page";
import { useAuth } from "../lib/auth/AuthProvider";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("../lib/auth/AuthProvider", () => ({
  useAuth: vi.fn(),
}));

describe("SignUpPage", () => {
  it("renders the sign-up heading and a link to sign-in", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      loading: false,
      signInWithGoogle: vi.fn(),
      signInWithEmail: vi.fn(),
      signUpWithEmail: vi.fn(),
      signOutUser: vi.fn(),
    });

    render(<SignUpPage />);

    expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in");
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

    render(<SignUpPage />);

    expect(replace).toHaveBeenCalledWith("/app");
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

    render(<SignUpPage />);

    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Too many attempts. Please wait a moment and try again.")
    );
  });
});
