"use client";

import { useRef } from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { useAuth } from "@/lib/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import { WatchingRings } from "./WatchingRings";
import { PhoneMockup } from "./PhoneMockup";
import { CaptionFeed } from "./CaptionFeed";

const EASE = [0.16, 1, 0.3, 1] as const;

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } },
};

export function HeroSection() {
  const { signInWithGoogle, loading } = useAuth();
  const prefersReducedMotion = useReducedMotion();
  const visualRef = useRef<HTMLDivElement>(null);

  function handleMouseMove(event: React.MouseEvent<HTMLDivElement>) {
    if (prefersReducedMotion) return;
    const node = visualRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    const dx = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
    const dy = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
    node.style.setProperty("--parallax-x", `${dx * -6}px`);
    node.style.setProperty("--parallax-y", `${dy * -6}px`);
  }

  function handleMouseLeave() {
    const node = visualRef.current;
    if (!node) return;
    node.style.setProperty("--parallax-x", "0px");
    node.style.setProperty("--parallax-y", "0px");
  }

  return (
    <section className="relative overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(640px circle at 78% 28%, hsl(var(--primary) / 0.14), hsl(var(--primary-deep) / 0.05) 55%, transparent 75%)",
        }}
        aria-hidden="true"
      />
      <motion.div
        variants={container}
        initial={prefersReducedMotion ? "show" : "hidden"}
        animate="show"
        className="relative mx-auto grid max-w-7xl grid-cols-1 items-center gap-12 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-2 lg:px-8 lg:py-32"
      >
        <div>
          <motion.p variants={item} className="text-sm font-medium uppercase tracking-wide text-primary">
            The agentic seeing-eye copilot
          </motion.p>
          <motion.h1
            variants={item}
            className="mt-4 text-balance text-5xl font-semibold tracking-tight sm:text-6xl lg:text-7xl"
          >
            Argus doesn&apos;t describe the world. It acts in it.
          </motion.h1>
          <motion.p variants={item} className="mt-6 max-w-xl text-pretty text-lg text-muted-foreground sm:text-xl">
            Say a goal out loud — reach your connecting train after a last-minute platform change, or resolve a
            pharmacy refill — and Argus perceives, plans, acts, and replans in real time until it&apos;s done.
          </motion.p>
          <motion.div variants={item} className="mt-10 flex flex-col gap-3 sm:flex-row">
            <Button size="lg" onClick={() => void signInWithGoogle()} disabled={loading}>
              Get started with Google
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href="#how-it-works">See how it works</a>
            </Button>
          </motion.div>
        </div>

        <motion.div
          variants={item}
          ref={visualRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          className="relative mx-auto flex w-full max-w-sm items-center justify-center"
          style={{
            transform: "translate3d(var(--parallax-x, 0px), var(--parallax-y, 0px), 0)",
            transition: "transform 200ms ease-out",
          }}
        >
          <WatchingRings rich className="absolute h-[420px] w-[420px]" />
          <PhoneMockup className="relative">
            <CaptionFeed lines={[{ speaker: "argus", text: "Platform changed. This way instead.", live: true }]} />
          </PhoneMockup>
        </motion.div>
      </motion.div>
    </section>
  );
}
