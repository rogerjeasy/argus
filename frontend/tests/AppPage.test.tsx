// frontend/tests/AppPage.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AppPage from "../app/app/page";
import { AuthProvider } from "../lib/auth/AuthProvider";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("../lib/auth/firebase", () => ({
  firebaseAuth: {},
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

describe("AppPage", () => {
  beforeEach(() => {
    replace.mockReset();
    authCallback = null;
  });

  it("redirects to / once auth resolves to signed-out", async () => {
    render(
      <AuthProvider>
        <AppPage />
      </AuthProvider>
    );
    authCallback?.(null);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
  });

  it("renders the session screen once auth resolves to signed-in", async () => {
    render(
      <AuthProvider>
        <AppPage />
      </AuthProvider>
    );
    authCallback?.({ uid: "user-1", getIdToken: () => Promise.resolve("fake-token") });
    await waitFor(() => expect(screen.getByRole("heading", { name: "Argus" })).toBeInTheDocument());
    expect(replace).not.toHaveBeenCalled();
  });
});
