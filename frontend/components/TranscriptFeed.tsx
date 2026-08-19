"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { cn } from "@/lib/utils";
import { isRtlLanguage } from "@/lib/session/protocol";
import type { TranscriptEntry } from "@/lib/session/useSession";

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const line: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: "easeOut" } },
};

/**
 * Bounded, real caption history (see useSession's transcriptHistory) — this
 * region carries the aria-live="polite" announcement role SessionControl's
 * old standalone captionText paragraph used to have; that paragraph is
 * removed once SessionControl is rebuilt, this is its replacement.
 */
export function TranscriptFeed({ entries }: { entries: TranscriptEntry[] }) {
  const prefersReducedMotion = useReducedMotion();

  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">What Argus says will appear here once your session starts.</p>;
  }

  return (
    <motion.ol
      aria-label="Recent guidance"
      aria-live="polite"
      variants={container}
      initial={prefersReducedMotion ? "show" : "hidden"}
      animate="show"
      className="flex max-h-64 flex-col gap-2 overflow-y-auto"
    >
      {entries.map((entry) => (
        <motion.li
          key={entry.id}
          variants={line}
          dir={isRtlLanguage(entry.language) ? "rtl" : "ltr"}
          className={cn("rounded-xl bg-secondary px-3 py-2 text-sm leading-snug text-foreground")}
        >
          {entry.text}
        </motion.li>
      ))}
    </motion.ol>
  );
}
