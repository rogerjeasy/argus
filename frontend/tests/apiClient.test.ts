import { describe, expect, it, vi } from "vitest";
import { apiFetch } from "../lib/api/client";

describe("apiFetch", () => {
  it("sends the bearer token and parses JSON", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ verbosity: "normal", pace: "normal" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const result = await apiFetch<{ verbosity: string; pace: string }>("/api/settings", {
      token: "abc123",
    });

    expect(result).toEqual({ verbosity: "normal", pace: "normal" });
    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer abc123");
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401, statusText: "Unauthorized" })
    );

    await expect(apiFetch("/api/settings")).rejects.toThrow("401");
  });
});
