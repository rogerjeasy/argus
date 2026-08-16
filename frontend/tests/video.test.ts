import { describe, expect, it } from "vitest";
import { describeCameraError } from "@/lib/session/video";

describe("describeCameraError", () => {
  it("explains a blocked camera permission in plain language", () => {
    const error = Object.assign(new Error(), { name: "NotAllowedError" });
    expect(describeCameraError(error)).toMatch(/camera access was blocked/i);
  });

  it("explains a missing camera in plain language", () => {
    const error = Object.assign(new Error(), { name: "NotFoundError" });
    expect(describeCameraError(error)).toMatch(/no camera was found/i);
  });

  it("falls back to a generic message for an unrecognized error", () => {
    expect(describeCameraError(new Error("boom"))).toMatch(/camera could not be started/i);
  });
});
