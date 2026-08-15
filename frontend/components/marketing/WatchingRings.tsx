import { cn } from "@/lib/utils";

/**
 * An abstract concentric-ring motif — a restrained nod to Argus's
 * hundred-eyed mythology without literally drawing an eye. Purely
 * decorative in every usage, so it's always aria-hidden.
 */
export function WatchingRings({ className, animated = true }: { className?: string; animated?: boolean }) {
  return (
    <svg
      viewBox="0 0 200 200"
      className={cn("text-primary", animated && "animate-watching-rings", className)}
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="100" cy="100" r="30" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.9" />
      <circle cx="100" cy="100" r="55" fill="none" stroke="currentColor" strokeWidth="1.25" opacity="0.55" />
      <circle cx="100" cy="100" r="80" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      <circle cx="100" cy="20" r="3" fill="currentColor" opacity="0.7" />
      <circle cx="176" cy="65" r="2.5" fill="currentColor" opacity="0.5" />
      <circle cx="176" cy="135" r="2" fill="currentColor" opacity="0.35" />
      <circle cx="24" cy="65" r="2.5" fill="currentColor" opacity="0.5" />
      <circle cx="24" cy="135" r="2" fill="currentColor" opacity="0.35" />
    </svg>
  );
}
