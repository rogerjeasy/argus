import Link from "next/link";
import { cn } from "@/lib/utils";
import { WatchingRings } from "./WatchingRings";

export function Logo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn(
        "group inline-flex min-h-11 -my-2 items-center gap-2 rounded-lg text-lg font-semibold tracking-tight text-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        className
      )}
    >
      <WatchingRings
        className="h-7 w-7 transition-transform duration-500 ease-out group-hover:rotate-[18deg] motion-reduce:transition-none motion-reduce:group-hover:rotate-0"
        animated={false}
      />
      <span>Argus</span>
    </Link>
  );
}
