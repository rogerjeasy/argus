import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MarketingNav } from "../components/marketing/MarketingNav";
import { AuthProvider } from "../lib/auth/AuthProvider";

vi.mock("../lib/auth/firebase", () => ({
  firebaseAuth: {},
}));

let authCallback: ((user: unknown) => void) | null = null;
const signInWithPopupMock = vi.fn();

vi.mock("firebase/auth", () => ({
  onAuthStateChanged: (_auth: unknown, callback: (user: unknown) => void) => {
    authCallback = callback;
    return () => {};
  },
  signInWithPopup: (...args: unknown[]) => signInWithPopupMock(...args),
  signOut: vi.fn(),
  GoogleAuthProvider: class {},
}));

function renderNav() {
  render(
    <AuthProvider>
      <MarketingNav />
    </AuthProvider>
  );
}

describe("MarketingNav", () => {
  beforeEach(() => {
    authCallback = null;
    signInWithPopupMock.mockReset();
  });

  it("triggers Google sign-in when a logged-out visitor clicks the CTA", async () => {
    renderNav();
    authCallback?.(null);
    const ctas = await waitFor(() => screen.getAllByRole("button", { name: "Sign in" }));

    ctas[0].click();
    expect(signInWithPopupMock).toHaveBeenCalled();
  });

  it("links a signed-in visitor to /app instead of prompting sign-in", async () => {
    renderNav();
    authCallback?.({ uid: "user-1" });

    const ctas = await screen.findAllByRole("link", { name: "Open Argus" });
    expect(ctas[0]).toHaveAttribute("href", "/app");
  });
});
