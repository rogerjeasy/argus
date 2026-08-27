import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FinalCta } from "../components/marketing/FinalCta";
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

describe("FinalCta", () => {
  beforeEach(() => {
    signInWithPopupMock.mockReset();
  });

  it("triggers Google sign-in from the closing CTA", () => {
    render(
      <AuthProvider>
        <FinalCta />
      </AuthProvider>
    );
    screen.getByRole("button", { name: "Get started with Google" }).click();
    expect(signInWithPopupMock).toHaveBeenCalled();
  });
});
