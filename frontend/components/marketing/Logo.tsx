import Link from "next/link";
import { cn } from "@/lib/utils";
import { WatchingRings } from "./WatchingRings";

export function Logo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn(
        "inline-flex min-h-11 -my-2 items-center gap-2 rounded-lg text-lg font-semibold tracking-tight text-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        className
      )}
    >
      <WatchingRings className="h-7 w-7" animated={false} />
      <span>Argus</span>
    </Link>
  );
}
