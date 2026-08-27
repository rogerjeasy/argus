import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HomeAuthGuard } from "../components/marketing/HomeAuthGuard";
import { AuthProvider } from "../lib/auth/AuthProvider";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("../lib/auth/firebase", () => ({
  getFirebaseAuth: () => ({}),
}));

let authCallback: ((user: unknown) => void) | null = null;

vi.mock("firebase/auth", () => ({
  onAuthStateChanged: (_auth: unknown, callback: (user: unknown) => void) => {
    authCallback = callback;
    return () => {};
  },
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
  GoogleAuthProvider: class {},
}));

function renderGuard() {
  render(
    <AuthProvider>
      <HomeAuthGuard>
        <div data-testid="marketing-content">Marketing content</div>
      </HomeAuthGuard>
    </AuthProvider>
  );
}

describe("HomeAuthGuard", () => {
  beforeEach(() => {
    replace.mockReset();
    authCallback = null;
  });

  it("renders children immediately and does not redirect while auth is still loading", () => {
    renderGuard();
    expect(screen.getByTestId("marketing-content")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("stays put and keeps rendering children once auth resolves to signed-out", async () => {
    renderGuard();
    authCallback?.(null);
    await waitFor(() => expect(replace).not.toHaveBeenCalled());
    expect(screen.getByTestId("marketing-content")).toBeInTheDocument();
  });

  it("redirects to /app once auth resolves to a signed-in user", async () => {
    renderGuard();
    authCallback?.({ uid: "user-1" });
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });
});
