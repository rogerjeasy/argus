// frontend/tests/HomePage.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import HomePage from "../app/page";
import { AuthProvider } from "../lib/auth/AuthProvider";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock("../lib/auth/firebase", () => ({
  firebaseAuth: {},
}));

vi.mock("firebase/auth", () => ({
  onAuthStateChanged: (_auth: unknown, callback: (user: unknown) => void) => {
    callback(null);
    return () => {};
  },
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
  GoogleAuthProvider: class {},
}));

describe("HomePage", () => {
  it("renders exactly one H1 and every landmark region", () => {
    render(
      <AuthProvider>
        <HomePage />
      </AuthProvider>
    );
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("renders a skip-to-content link targeting the main landmark", () => {
    render(
      <AuthProvider>
        <HomePage />
      </AuthProvider>
    );
    expect(screen.getByRole("link", { name: "Skip to content" })).toHaveAttribute("href", "#main-content");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
  });
});
