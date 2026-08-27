import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HeroSection } from "../components/marketing/HeroSection";
import { AuthProvider } from "../lib/auth/AuthProvider";

vi.mock("../lib/auth/firebase", () => ({
  getFirebaseAuth: () => ({}),
}));

const signInWithPopupMock = vi.fn();

vi.mock("firebase/auth", () => ({
  onAuthStateChanged: (_auth: unknown, callback: (user: unknown) => void) => {
    callback(null);
    return () => {};
  },
  signInWithPopup: (...args: unknown[]) => signInWithPopupMock(...args),
  signOut: vi.fn(),
  GoogleAuthProvider: class {},
}));

function renderHero() {
  render(
    <AuthProvider>
      <HeroSection />
    </AuthProvider>
  );
}

describe("HeroSection", () => {
  beforeEach(() => {
    signInWithPopupMock.mockReset();
  });

  it("renders the page's H1 and triggers sign-in from the primary CTA", () => {
    renderHero();
    expect(screen.getByRole("heading", { level: 1, name: /doesn't describe the world/i })).toBeInTheDocument();

    screen.getByRole("button", { name: "Get started with Google" }).click();
    expect(signInWithPopupMock).toHaveBeenCalled();
  });

  it("links the secondary CTA to the how-it-works anchor", () => {
    renderHero();
    expect(screen.getByRole("link", { name: "See how it works" })).toHaveAttribute("href", "#how-it-works");
  });
});
