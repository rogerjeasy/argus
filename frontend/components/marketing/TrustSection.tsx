"use client";

import { EyeOff, KeyRound, Lock, ShieldCheck } from "lucide-react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Reveal } from "./Reveal";
import { TrustPoint } from "./TrustPoint";

// A calm, one-time stagger only — no continuous motion. Busy motion here
// would undercut the section's "reassuring" register.
const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

export function TrustSection() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <section id="trust" aria-labelledby="trust-heading" className="border-t border-border">
      <Reveal className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 id="trust-heading" className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Autonomy is earned, never assumed.
          </h2>
          <p className="mt-4 text-pretty text-lg text-muted-foreground">
            A camera pointed at the real world, and a task that can touch real money and real deadlines — this is
            core architecture, not an afterthought.
          </p>
        </div>

        <motion.div
          variants={container}
          initial={prefersReducedMotion ? "show" : "hidden"}
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          className="mx-auto mt-14 grid max-w-4xl grid-cols-1 gap-x-10 gap-y-10 sm:grid-cols-2"
        >
          <motion.div variants={item}>
            <TrustPoint
              icon={EyeOff}
              title="No raw video, ever stored"
              description="Frames are processed ephemerally. Only structured, task-relevant signals cross into the rest of the system."
            />
          </motion.div>
          <motion.div variants={item}>
            <TrustPoint
              icon={ShieldCheck}
              title="Tiered autonomy, never blanket autonomy"
              description="Routine, previously-approved actions proceed automatically. Anything financial, medical, or unprecedented always asks first."
            />
          </motion.div>
          <motion.div variants={item}>
            <TrustPoint
              icon={Lock}
              title="Inbound content is untrusted"
              description="A scanned letter or live IVR audio is screened the same way a scraped web page would be — never treated as a standing permission."
            />
          </motion.div>
          <motion.div variants={item}>
            <TrustPoint
              icon={KeyRound}
              title="Encrypted at rest"
              description="Medical- and financial-adjacent profile fields are encrypted specifically, on top of standard data protection."
            />
          </motion.div>
        </motion.div>
      </Reveal>
    </section>
  );
}
