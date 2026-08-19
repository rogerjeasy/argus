import { mkdir } from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

// The real, exact concentric-ring motif from
// components/marketing/WatchingRings.tsx, with `currentColor` resolved to
// the literal --primary hex since a static PNG has no CSS custom-property
// context. Kept in sync by hand — if that component's geometry changes,
// regenerate these icons too.
const PRIMARY = "#1B5E77";

function watchingRingsSvg({ background, scale = 1 } = {}) {
  const transform = scale < 1 ? `translate(${100 - 100 * scale} ${100 - 100 * scale}) scale(${scale})` : "";
  return `
<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  ${background ? `<rect width="200" height="200" fill="${background}" />` : ""}
  <g ${transform ? `transform="${transform}"` : ""}>
    <circle cx="100" cy="100" r="30" fill="none" stroke="${PRIMARY}" stroke-width="1.5" opacity="0.9" />
    <circle cx="100" cy="100" r="55" fill="none" stroke="${PRIMARY}" stroke-width="1.25" opacity="0.55" />
    <circle cx="100" cy="100" r="80" fill="none" stroke="${PRIMARY}" stroke-width="1" opacity="0.3" />
    <circle cx="100" cy="20" r="3" fill="${PRIMARY}" opacity="0.7" />
    <circle cx="176" cy="65" r="2.5" fill="${PRIMARY}" opacity="0.5" />
    <circle cx="176" cy="135" r="2" fill="${PRIMARY}" opacity="0.35" />
    <circle cx="24" cy="65" r="2.5" fill="${PRIMARY}" opacity="0.5" />
    <circle cx="24" cy="135" r="2" fill="${PRIMARY}" opacity="0.35" />
  </g>
</svg>`;
}

async function main() {
  const publicDir = path.resolve(import.meta.dirname, "..", "public");
  const appDir = path.resolve(import.meta.dirname, "..", "app");
  await mkdir(publicDir, { recursive: true });

  const standard = watchingRingsSvg({ background: "#FFFFFF" });
  await sharp(Buffer.from(standard)).resize(192, 192).png().toFile(path.join(publicDir, "icon-192.png"));
  await sharp(Buffer.from(standard)).resize(512, 512).png().toFile(path.join(publicDir, "icon-512.png"));
  await sharp(Buffer.from(standard)).resize(180, 180).png().toFile(path.join(appDir, "apple-icon.png"));

  // Maskable: mark scaled to 70% of the canvas so the outer ring/dots
  // survive a circular or squircle crop on any platform without clipping.
  const maskable = watchingRingsSvg({ background: "#FFFFFF", scale: 0.7 });
  await sharp(Buffer.from(maskable)).resize(512, 512).png().toFile(path.join(publicDir, "icon-maskable.png"));

  console.log("Generated icon-192.png, icon-512.png, icon-maskable.png in frontend/public/, apple-icon.png in frontend/app/");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
