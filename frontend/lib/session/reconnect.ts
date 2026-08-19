/**
 * Bounded exponential backoff for an unexpected mid-session disconnect —
 * "a short network gap" per the design doc's own example (underground
 * platforms). Not derived from real network-interruption data; tune once
 * real usage exists (pre-demo checklist).
 */
export const RECONNECT_MAX_ATTEMPTS = 5;

export function reconnectDelayMs(attempt: number): number {
  return 1000 * 2 ** (attempt - 1);
}
