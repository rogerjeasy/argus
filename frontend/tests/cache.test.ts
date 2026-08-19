import { beforeEach } from "vitest";
import { saveCachedGuidance, loadCachedGuidance, clearCachedGuidance } from "@/lib/session/cache";

beforeEach(() => {
  localStorage.clear();
});

test("round-trips through localStorage", () => {
  saveCachedGuidance({ captionText: "Head to platform 4.", framingText: null, captionLanguage: "en" });

  expect(loadCachedGuidance()).toEqual({ captionText: "Head to platform 4.", framingText: null, captionLanguage: "en" });
});

test("returns null when nothing has been cached", () => {
  expect(loadCachedGuidance()).toBeNull();
});

test("clearCachedGuidance removes it", () => {
  saveCachedGuidance({ captionText: "x", framingText: "y", captionLanguage: "en" });
  clearCachedGuidance();

  expect(loadCachedGuidance()).toBeNull();
});

test("malformed stored JSON is treated as no cache, not a thrown error", () => {
  localStorage.setItem("argus:cached-guidance", "not json");

  expect(loadCachedGuidance()).toBeNull();
});
