import { describe, expect, it } from "vitest";
import { firebaseAuthErrorMessage } from "../lib/auth/errors";

describe("firebaseAuthErrorMessage", () => {
  it("maps a known Firebase error code to plain-language copy", () => {
    expect(firebaseAuthErrorMessage({ code: "auth/email-already-in-use" })).toBe(
      "An account with that email already exists. Try signing in instead."
    );
  });

  it("falls back to a generic message for an unrecognized code", () => {
    expect(firebaseAuthErrorMessage({ code: "auth/some-new-error" })).toBe("Something went wrong. Please try again.");
  });

  it("falls back to a generic message for a non-Firebase error", () => {
    expect(firebaseAuthErrorMessage(new Error("network down"))).toBe("Something went wrong. Please try again.");
  });
});
