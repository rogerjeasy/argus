import { describe, expect, it } from "vitest";
import { deriveStageState, type StageStateInput } from "@/lib/session/stageState";

const BASE: StageStateInput = {
  status: "idle", guardrailDecision: null, usingCachedGuidance: false, playbackLevel: 0,
};

describe("deriveStageState", () => {
  it("is idle when nothing is happening", () => {
    expect(deriveStageState(BASE)).toBe("idle");
  });

  it("is connecting while the socket handshakes", () => {
    expect(deriveStageState({ ...BASE, status: "connecting" })).toBe("connecting");
  });

  it("is listening once connected with no playback", () => {
    expect(deriveStageState({ ...BASE, status: "connected" })).toBe("listening");
  });

  it("is speaking once connected with a nonzero playback level", () => {
    expect(deriveStageState({ ...BASE, status: "connected", playbackLevel: 0.4 })).toBe("speaking");
  });

  it("is guardrail-pending when a confirmation is required, even while connected and speaking", () => {
    expect(
      deriveStageState({ ...BASE, status: "connected", playbackLevel: 0.4, guardrailDecision: "requires_confirmation" })
    ).toBe("guardrail-pending");
  });

  it("is guardrail-pending for requires_field_input too", () => {
    expect(deriveStageState({ ...BASE, status: "connected", guardrailDecision: "requires_field_input" })).toBe(
      "guardrail-pending"
    );
  });

  it("is NOT guardrail-pending for approved or denied — those don't block the stage", () => {
    expect(deriveStageState({ ...BASE, status: "connected", guardrailDecision: "approved" })).toBe("listening");
    expect(deriveStageState({ ...BASE, status: "connected", guardrailDecision: "denied" })).toBe("listening");
  });

  it("is degraded while reconnecting", () => {
    expect(deriveStageState({ ...BASE, status: "reconnecting" })).toBe("degraded");
  });

  it("is degraded whenever cached guidance is in use, regardless of status", () => {
    expect(deriveStageState({ ...BASE, status: "connected", usingCachedGuidance: true })).toBe("degraded");
  });

  it("is error when the session errored, taking priority over everything else", () => {
    expect(
      deriveStageState({ status: "error", guardrailDecision: "requires_confirmation", usingCachedGuidance: true, playbackLevel: 0.9 })
    ).toBe("error");
  });
});
