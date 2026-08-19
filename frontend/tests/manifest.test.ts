import { describe, expect, it } from "vitest";
import manifest from "@/app/manifest";

describe("PWA manifest", () => {
  it("declares a standalone app starting at /app with the real brand tokens", () => {
    const result = manifest();
    expect(result.name).toMatch(/argus/i);
    expect(result.short_name).toBe("Argus");
    expect(result.start_url).toBe("/app");
    expect(result.display).toBe("standalone");
    // Must match app/globals.css's own token comments exactly:
    // --primary: 198 65% 32%; /* #1B5E77 harbor blue */
    // --background: 210 20% 98%; /* #F7F9FA */
    expect(result.theme_color).toBe("#1B5E77");
    expect(result.background_color).toBe("#F7F9FA");
  });

  it("declares 192, 512, and a maskable 512 icon", () => {
    const result = manifest();
    const sizes = result.icons?.map((icon) => icon.sizes);
    expect(sizes).toContain("192x192");
    expect(sizes).toContain("512x512");
    expect(result.icons?.some((icon) => icon.purpose === "maskable")).toBe(true);
  });
});
