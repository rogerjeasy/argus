import { render, screen, waitFor } from "@testing-library/react";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  updateProfile,
} from "firebase/auth";
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
  signInWithEmailAndPassword: vi.fn(),
  createUserWithEmailAndPassword: vi.fn(),
  updateProfile: vi.fn(),
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
    vi.mocked(signInWithEmailAndPassword).mockReset();
    vi.mocked(createUserWithEmailAndPassword).mockReset();
    vi.mocked(updateProfile).mockReset();
    vi.unstubAllGlobals();
  });

  it("resolves to signed-out once Firebase reports no user", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("signed-out"));
  });

  it("propagates a signInWithGoogle rejection so the caller's form can show it", async () => {
    vi.mocked(signInWithPopup).mockRejectedValue(new Error("popup closed by user"));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("signed-out"));

    await expect(capturedAuth?.signInWithGoogle()).rejects.toThrow("popup closed by user");
    // loading should not be stuck as a side effect of the rejected sign-in attempt.
    expect(screen.getByTestId("probe").textContent).toBe("signed-out");
  });

  it("signs in with email/password and syncs the profile", async () => {
    const fakeUser = { uid: "user-1", getIdToken: vi.fn().mockResolvedValue("id-token") };
    vi.mocked(signInWithEmailAndPassword).mockResolvedValue({ user: fakeUser } as never);
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("signed-out"));

    await capturedAuth?.signInWithEmail("a@example.com", "pw123456");

    expect(signInWithEmailAndPassword).toHaveBeenCalledWith(expect.anything(), "a@example.com", "pw123456");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/users/me"),
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("propagates a signInWithEmail rejection so the caller's form can show it", async () => {
    vi.mocked(signInWithEmailAndPassword).mockRejectedValue({ code: "auth/wrong-password" });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("signed-out"));

    await expect(capturedAuth?.signInWithEmail("a@example.com", "wrong")).rejects.toMatchObject({
      code: "auth/wrong-password",
    });
  });

  it("signs up with email/password, sets the display name, and syncs the profile", async () => {
    const fakeUser = { uid: "user-2", getIdToken: vi.fn().mockResolvedValue("id-token") };
    vi.mocked(createUserWithEmailAndPassword).mockResolvedValue({ user: fakeUser } as never);
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("signed-out"));

    await capturedAuth?.signUpWithEmail("a@example.com", "pw123456", "Ada Lovelace");

    expect(createUserWithEmailAndPassword).toHaveBeenCalledWith(expect.anything(), "a@example.com", "pw123456");
    expect(updateProfile).toHaveBeenCalledWith(fakeUser, { displayName: "Ada Lovelace" });
    expect(fetchMock).toHaveBeenCalled();
  });

  it("does not let a profile-sync failure block Google sign-in from resolving", async () => {
    const fakeUser = {
      uid: "user-3",
      displayName: null,
      photoURL: null,
      getIdToken: vi.fn().mockResolvedValue("id-token"),
    };
    vi.mocked(signInWithPopup).mockResolvedValue({ user: fakeUser } as never);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("signed-out"));

    await expect(capturedAuth?.signInWithGoogle()).resolves.toBeUndefined();
  });
});
