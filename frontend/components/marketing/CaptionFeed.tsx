"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { cn } from "@/lib/utils";

export interface CaptionLine {
  speaker: "argus" | "user";
  text: string;
  live?: boolean;
}

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.35, delayChildren: 0.1 } },
};

const bubble: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] } },
};

// Bubbles appear one at a time, like watching the transcript happen live,
// rather than all present at once.
export function CaptionFeed({ lines }: { lines: CaptionLine[] }) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.ol
      aria-label="Live caption transcript"
      variants={container}
      initial={prefersReducedMotion ? "show" : "hidden"}
      whileInView="show"
      viewport={{ once: true, margin: "-40px" }}
      className="flex flex-col gap-3"
    >
      {lines.map((line, index) => (
        <motion.li
          key={index}
          variants={bubble}
          className={cn(
            "flex flex-col gap-1 rounded-xl px-3 py-2 text-sm leading-snug",
            line.speaker === "argus" ? "bg-primary/10 text-foreground" : "self-end bg-secondary text-foreground"
          )}
        >
          <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            {line.speaker === "argus" ? "Argus" : "You"}
            {line.live && (
              <span className="inline-flex items-center gap-1 text-accent">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" aria-hidden="true" />
                live
              </span>
            )}
          </span>
          <span>{line.text}</span>
        </motion.li>
      ))}
    </motion.ol>
  );
}
