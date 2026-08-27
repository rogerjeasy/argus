import { describe, expect, it } from "vitest";
import { APP_NAV_ITEMS } from "@/lib/app-nav";

describe("APP_NAV_ITEMS", () => {
  it("has exactly the 4 real, data-backed destinations", () => {
    expect(APP_NAV_ITEMS.map((item) => item.href)).toEqual(["/dashboard", "/dashboard/history", "/dashboard/settings", "/dashboard/contacts"]);
  });

  it("every item has a non-empty label and an icon", () => {
    for (const item of APP_NAV_ITEMS) {
      expect(item.label.length).toBeGreaterThan(0);
      expect(item.icon).toBeDefined();
    }
  });
});
