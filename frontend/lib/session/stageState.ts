import type { GuardrailDecisionValue } from "./protocol";

export type StageState =
  | "idle"
  | "connecting"
  | "listening"
  | "speaking"
  | "guardrail-pending"
  | "degraded"
  | "error";

export interface StageStateInput {
  status: "idle" | "connecting" | "connected" | "reconnecting" | "error";
  guardrailDecision: GuardrailDecisionValue | null;
  usingCachedGuidance: boolean;
  playbackLevel: number;
}

/**
 * The Session Stage's single source of truth for which of 7 visual states
 * to show. Priority order matters: error and degraded-connectivity outrank
 * everything else (they're about whether the channel is trustworthy at
 * all), guardrail-pending outranks the audio-driven listening/speaking
 * split (a pending confirmation blocks the flow regardless of what's
 * playing), and listening vs. speaking is decided last, purely by whether
 * anything is audibly playing back right now.
 */
export function deriveStageState(input: StageStateInput): StageState {
  const { status, guardrailDecision, usingCachedGuidance, playbackLevel } = input;

  if (status === "error") return "error";
  if (usingCachedGuidance || status === "reconnecting") return "degraded";
  if (guardrailDecision === "requires_confirmation" || guardrailDecision === "requires_field_input") {
    return "guardrail-pending";
  }
  if (status === "connecting") return "connecting";
  if (status === "connected" && playbackLevel > 0) return "speaking";
  if (status === "connected") return "listening";
  return "idle";
}
