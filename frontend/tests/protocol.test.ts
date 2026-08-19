import { describe, expect, it, test, vi } from "vitest";
import { isRtlLanguage, parseControlFrame, parseFramingFrame } from "@/lib/session/protocol";

describe("parseControlFrame", () => {
  it("parses a well-formed guidance frame", () => {
    const frame = parseControlFrame(
      JSON.stringify({
        type: "guidance",
        text: "Head to platform 4.",
        haptic_pattern: "pattern-forward",
        earcon: "earcon-plan-updated",
        guardrail_decision: "requires_confirmation",
        step_id: "step-1",
      })
    );
    expect(frame).toEqual({
      type: "guidance",
      text: "Head to platform 4.",
      hapticPattern: "pattern-forward",
      earcon: "earcon-plan-updated",
      guardrailDecision: "requires_confirmation",
      stepId: "step-1",
      fieldLabel: null,
      language: "en",
    });
  });

  it("parses the language field, defaulting to en when absent", () => {
    const withLanguage = parseControlFrame(
      JSON.stringify({
        type: "guidance", text: "פנה שמאלה.", guardrail_decision: "approved", step_id: "s1", language: "he",
      })
    );
    expect(withLanguage?.language).toBe("he");

    const withoutLanguage = parseControlFrame(
      JSON.stringify({ type: "guidance", text: "Turn left.", guardrail_decision: "approved", step_id: "s1" })
    );
    expect(withoutLanguage?.language).toBe("en");
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

  it("captures field_label for a requires_field_input frame", () => {
    const frame = parseControlFrame(
      JSON.stringify({
        type: "guidance",
        text: "What's your policy number?",
        guardrail_decision: "requires_field_input",
        step_id: "step-1",
        field_label: "Policy number",
      })
    );
    expect(frame?.fieldLabel).toBe("Policy number");
  });
});

test("parseControlFrame captures step_id for the confirmation round trip", () => {
  const frame = parseControlFrame(
    JSON.stringify({ type: "guidance", text: "hi", guardrail_decision: "requires_confirmation", step_id: "s1" })
  );

  expect(frame?.stepId).toBe("s1");
});

test("isRtlLanguage is true only for Arabic and Hebrew", () => {
  expect(isRtlLanguage("ar")).toBe(true);
  expect(isRtlLanguage("he")).toBe(true);
  expect(isRtlLanguage("en")).toBe(false);
  expect(isRtlLanguage("de")).toBe(false);
});

describe("parseFramingFrame", () => {
  it("parses a well-formed framing frame", () => {
    const frame = parseFramingFrame(JSON.stringify({ type: "framing", text: "Move slightly right.", confidence_low: false }));
    expect(frame).toEqual({ type: "framing", text: "Move slightly right.", confidenceLow: false });
  });

  it("returns null for a non-framing frame", () => {
    expect(parseFramingFrame(JSON.stringify({ type: "guidance", text: "x" }))).toBeNull();
  });

  it("returns null for malformed JSON without throwing", () => {
    expect(parseFramingFrame("{not json")).toBeNull();
  });
});
