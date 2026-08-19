import { RECONNECT_MAX_ATTEMPTS, reconnectDelayMs } from "@/lib/session/reconnect";

test("delay grows exponentially with each attempt", () => {
  expect(reconnectDelayMs(1)).toBe(1000);
  expect(reconnectDelayMs(2)).toBe(2000);
  expect(reconnectDelayMs(3)).toBe(4000);
  expect(reconnectDelayMs(4)).toBe(8000);
});

test("RECONNECT_MAX_ATTEMPTS is a small positive bound", () => {
  expect(RECONNECT_MAX_ATTEMPTS).toBeGreaterThan(0);
  expect(RECONNECT_MAX_ATTEMPTS).toBeLessThanOrEqual(10);
});
