import { describe, expect, it, vi } from "vitest";
import { parseControlFrame } from "@/lib/session/protocol";

describe("parseControlFrame", () => {
  it("parses a well-formed guidance frame", () => {
    const frame = parseControlFrame(
      JSON.stringify({
        type: "guidance",
        text: "Head to platform 4.",
        haptic_pattern: "pattern-forward",
        earcon: "earcon-plan-updated",
        guardrail_decision: "requires_confirmation",
      })
    );
    expect(frame).toEqual({
      type: "guidance",
      text: "Head to platform 4.",
      hapticPattern: "pattern-forward",
      earcon: "earcon-plan-updated",
      guardrailDecision: "requires_confirmation",
    });
  });

  it("returns null and logs on malformed JSON instead of throwing", () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(parseControlFrame("not json")).toBeNull();
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it("returns null for a well-formed but unrecognized frame type", () => {
    expect(parseControlFrame(JSON.stringify({ type: "unknown" }))).toBeNull();
  });
});
