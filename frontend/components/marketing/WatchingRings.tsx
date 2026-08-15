import { cn } from "@/lib/utils";

/**
 * An abstract concentric-ring motif — a restrained nod to Argus's
 * hundred-eyed mythology without literally drawing an eye. Purely
 * decorative in every usage, so it's always aria-hidden.
 *
 * `rich` adds a second, thinner ring with a slow gradient-sweep stroke —
 * reserved for hero scale, per the visual-refresh design (§6): the motif
 * stays simpler at the smaller CTA/footer scale so it doesn't compete
 * there. Independent of `animated`, and respects the same global
 * prefers-reduced-motion collapse everything else on the page does.
 */
export function WatchingRings({
  className,
  animated = true,
  rich = false,
}: {
  className?: string;
  animated?: boolean;
  rich?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 200 200"
      className={cn("text-primary", animated && "animate-watching-rings", className)}
      aria-hidden="true"
      focusable="false"
    >
      {rich && (
        <defs>
          <linearGradient id="watching-rings-sweep" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="200" y2="200">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0" />
            <stop offset="50%" stopColor="currentColor" stopOpacity="0.8" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </linearGradient>
        </defs>
      )}
      <circle cx="100" cy="100" r="30" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.9" />
      <circle cx="100" cy="100" r="55" fill="none" stroke="currentColor" strokeWidth="1.25" opacity="0.55" />
      <circle cx="100" cy="100" r="80" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      {rich && (
        <circle
          cx="100"
          cy="100"
          r="94"
          fill="none"
          stroke="url(#watching-rings-sweep)"
          strokeWidth="1"
          className={animated ? "animate-watching-sweep" : undefined}
        />
      )}
      <circle cx="100" cy="20" r="3" fill="currentColor" opacity="0.7" />
      <circle cx="176" cy="65" r="2.5" fill="currentColor" opacity="0.5" />
      <circle cx="176" cy="135" r="2" fill="currentColor" opacity="0.35" />
      <circle cx="24" cy="65" r="2.5" fill="currentColor" opacity="0.5" />
      <circle cx="24" cy="135" r="2" fill="currentColor" opacity="0.35" />
    </svg>
  );
}
