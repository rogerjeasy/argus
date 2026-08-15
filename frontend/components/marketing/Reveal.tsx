"use client";

import { useInView } from "@/lib/hooks/useInView";
import { cn } from "@/lib/utils";

export function Reveal({ children, className }: { children: React.ReactNode; className?: string }) {
  const { ref, inView } = useInView<HTMLDivElement>();

  return (
    <div
      ref={ref}
      className={cn(
        "transition-all duration-500 ease-out",
        inView ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0",
        className
      )}
    >
      {children}
    </div>
  );
}
