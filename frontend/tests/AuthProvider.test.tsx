import { render, screen, waitFor } from "@testing-library/react";
import { signInWithPopup } from "firebase/auth";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "../lib/auth/AuthProvider";

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

let capturedAuth: ReturnType<typeof useAuth> | null = null;

function Probe() {
  const auth = useAuth();
  capturedAuth = auth;
  const { user, loading } = auth;
  return <div data-testid="probe">{loading ? "loading" : user ? "signed-in" : "signed-out"}</div>;
}

describe("AuthProvider", () => {
  afterEach(() => {
    capturedAuth = null;
    vi.mocked(signInWithPopup).mockReset();
  });

  it("resolves to signed-out once Firebase reports no user", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("signed-out"));
  });

  it("swallows a signInWithPopup rejection instead of throwing", async () => {
    vi.mocked(signInWithPopup).mockRejectedValue(new Error("popup closed by user"));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("signed-out"));

    await expect(capturedAuth?.signInWithGoogle()).resolves.toBeUndefined();
    // loading should not be stuck as a side effect of the rejected sign-in attempt.
    expect(screen.getByTestId("probe").textContent).toBe("signed-out");
  });
});
