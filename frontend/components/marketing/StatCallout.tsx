"use client";

import { useEffect, useRef, useState } from "react";
import { animate, useInView, useReducedMotion } from "framer-motion";

export interface StatCountUp {
  target: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
}

export interface StatCalloutProps {
  /** Final display value, e.g. "2.2B", "43M", "0 of 5". */
  display: string;
  label: string;
  /** If provided, the numeric portion counts up from 0 on scroll-into-view. */
  countUp?: StatCountUp;
}

function formatCount(value: number, countUp: StatCountUp) {
  const { decimals = 0, prefix = "", suffix = "" } = countUp;
  return `${prefix}${value.toFixed(decimals)}${suffix}`;
}

export function StatCallout({ display, label, countUp }: StatCalloutProps) {
  const ref = useRef<HTMLParagraphElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const prefersReducedMotion = useReducedMotion();
  const [text, setText] = useState(() => (countUp ? formatCount(0, countUp) : display));

  useEffect(() => {
    if (!countUp) return;
    if (prefersReducedMotion) {
      setText(display);
      return;
    }
    if (!inView) return;
    const controls = animate(0, countUp.target, {
      duration: 1.2,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (value) => setText(formatCount(value, countUp)),
    });
    return () => controls.stop();
  }, [countUp, display, inView, prefersReducedMotion]);

  return (
    <div className="rounded-xl border border-border bg-card p-6 text-center shadow-sm transition-shadow duration-200 hover:shadow-[0_0_0_1px_hsl(var(--primary)/0.3),0_10px_28px_-10px_hsl(var(--primary)/0.35)] sm:p-8">
      <p ref={ref} className="text-4xl font-semibold tracking-tight text-primary sm:text-5xl">
        {text}
      </p>
      <p className="mt-2 text-pretty text-sm text-muted-foreground sm:text-base">{label}</p>
    </div>
  );
}
