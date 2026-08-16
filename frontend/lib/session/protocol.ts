export type GuardrailDecisionValue = "approved" | "requires_confirmation" | "denied";

export interface GuidanceFrame {
  type: "guidance";
  text: string;
  hapticPattern: string | null;
  earcon: string | null;
  guardrailDecision: GuardrailDecisionValue;
  stepId: string;
}

/**
 * Parses one JSON control frame from the WebSocket. Never throws — a
 * malformed or unrecognized frame from the server must not crash the
 * session UI, so this logs and returns null instead.
 */
export function parseControlFrame(raw: string): GuidanceFrame | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch (error) {
    console.error("Failed to parse WebSocket control frame", error);
    return null;
  }

  if (
    typeof payload !== "object" ||
    payload === null ||
    (payload as { type?: unknown }).type !== "guidance"
  ) {
    return null;
  }

  const frame = payload as Record<string, unknown>;
  if (typeof frame.text !== "string" || typeof frame.guardrail_decision !== "string" || typeof frame.step_id !== "string") {
    console.error("Guidance frame missing required fields", frame);
    return null;
  }

  return {
    type: "guidance",
    text: frame.text,
    hapticPattern: typeof frame.haptic_pattern === "string" ? frame.haptic_pattern : null,
    earcon: typeof frame.earcon === "string" ? frame.earcon : null,
    guardrailDecision: frame.guardrail_decision as GuardrailDecisionValue,
    stepId: frame.step_id,
  };
}

export interface FramingFrame {
  type: "framing";
  text: string;
  confidenceLow: boolean;
}

/**
 * Parses one JSON "framing" control frame from the WebSocket — camera
 * framing guidance (see backend/app/agents/guidance.py's shape_framing()).
 * Never throws, same contract as parseControlFrame.
 */
export function parseFramingFrame(raw: string): FramingFrame | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch (error) {
    console.error("Failed to parse WebSocket control frame", error);
    return null;
  }

  if (typeof payload !== "object" || payload === null || (payload as { type?: unknown }).type !== "framing") {
    return null;
  }

  const frame = payload as Record<string, unknown>;
  if (typeof frame.text !== "string" || typeof frame.confidence_low !== "boolean") {
    console.error("Framing frame missing required fields", frame);
    return null;
  }

  return { type: "framing", text: frame.text, confidenceLow: frame.confidence_low };
}

/**
 * Sends the resolve_confirmation control message back to the server — the
 * one path a tapped ConfirmationPrompt button uses. A spoken "yes" resolves
 * the same pending step through a completely different route (the user's
 * transcribed speech, handled server-side in TaskOrchestrator.handle_goal);
 * both converge on the same TaskOrchestrator.resolve_confirmation call.
 */
export function sendResolveConfirmation(socket: WebSocket, stepId: string, accepted: boolean): void {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "resolve_confirmation", step_id: stepId, accepted }));
  }
}
