import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { useIdToken } from "@/lib/auth/useIdToken";
import { useAuth } from "@/lib/auth/AuthProvider";

vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: vi.fn() }));

beforeEach(() => {
  vi.mocked(useAuth).mockReset();
});

test("returns null while signed out", () => {
  vi.mocked(useAuth).mockReturnValue({ user: null } as never);
  const { result } = renderHook(() => useIdToken());
  expect(result.current).toBeNull();
});

test("resolves the signed-in user's ID token", async () => {
  vi.mocked(useAuth).mockReturnValue({
    user: { getIdToken: vi.fn().mockResolvedValue("fake-token") },
  } as never);
  const { result } = renderHook(() => useIdToken());
  await waitFor(() => expect(result.current).toBe("fake-token"));
});

test("returns to null when the signed-in user becomes null", async () => {
  vi.mocked(useAuth).mockReturnValue({
    user: { getIdToken: vi.fn().mockResolvedValue("fake-token") },
  } as never);
  const { result, rerender } = renderHook(() => useIdToken());
  await waitFor(() => expect(result.current).toBe("fake-token"));

  vi.mocked(useAuth).mockReturnValue({ user: null } as never);
  rerender();
  await waitFor(() => expect(result.current).toBeNull());
});
