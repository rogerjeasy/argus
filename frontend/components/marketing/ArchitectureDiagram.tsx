"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";

/**
 * The Architecture section's signature visual: an engineering-schematic
 * diagram, not a glowing circuit-node network — right-angle connectors, a
 * dot-grid backdrop, monospace labels. Deliberately monochrome (every
 * stroke and fill derives from --surface-inverted-foreground at varying
 * opacity) so it reads as a real technical diagram and stays correct
 * across every theme, including high-contrast, without a dedicated hue.
 *
 * Perception -> Grounding+Guardrail -> Guidance form the core spine;
 * Grounding+Guardrail is the one solid-filled panel, visualizing the
 * system's trust boundary. Memory, Replanning, Escalation, and
 * Self-Calibration hang off a shared support bus beneath it.
 *
 * On scroll-into-view, connectors draw themselves in dependency order and
 * a single signal dot then loops along the core spine — animating "
 * Perception never talks directly to Guidance" instead of just captioning
 * it. Both behaviors are skipped under prefers-reduced-motion.
 */

const EASE = [0.16, 1, 0.3, 1] as const;

const nodeVariants: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  show: { opacity: 1, scale: 1, transition: { duration: 0.45, ease: EASE } },
};

const lineVariants: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  show: { pathLength: 1, opacity: 1, transition: { duration: 0.5, ease: EASE } },
};

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
};

const SATELLITES = [
  { label: "MEMORY", cx: 150 },
  { label: "REPLANNING", cx: 350 },
  { label: "ESCALATION", cx: 550 },
  { label: "SELF-CALIBRATION", cx: 750 },
];

export function ArchitectureDiagram() {
  const prefersReducedMotion = useReducedMotion();
  const stroke = "hsl(var(--surface-inverted-foreground) / 0.35)";
  const strokeStrong = "hsl(var(--surface-inverted-foreground) / 0.75)";
  const fg = "hsl(var(--surface-inverted-foreground))";

  return (
    <div className="bg-dot-grid mx-auto max-w-4xl rounded-2xl border border-surface-inverted-foreground/10 px-4 py-10 sm:px-8">
      <motion.svg
        viewBox="0 0 900 420"
        className="mx-auto w-full max-w-3xl"
        role="img"
        aria-label="Perception feeds into a Grounding and Guardrail trust boundary, which alone feeds Guidance. Memory, Replanning, Escalation, and Self-Calibration support that core line."
        variants={container}
        initial={prefersReducedMotion ? "show" : "hidden"}
        whileInView="show"
        viewport={{ once: true, margin: "-100px" }}
      >
        {/* core spine connectors */}
        <motion.line variants={lineVariants} x1="230" y1="90" x2="355" y2="90" stroke={strokeStrong} strokeWidth="1.5" />
        <motion.line variants={lineVariants} x1="545" y1="90" x2="670" y2="90" stroke={strokeStrong} strokeWidth="1.5" />

        {/* support bus */}
        <motion.line variants={lineVariants} x1="450" y1="145" x2="450" y2="300" stroke={stroke} strokeWidth="1" strokeDasharray="4 4" />
        <motion.line variants={lineVariants} x1="150" y1="300" x2="750" y2="300" stroke={stroke} strokeWidth="1" strokeDasharray="4 4" />
        {SATELLITES.map((s) => (
          <motion.line
            key={s.label}
            variants={lineVariants}
            x1={s.cx}
            y1="300"
            x2={s.cx}
            y2="340"
            stroke={stroke}
            strokeWidth="1"
            strokeDasharray="4 4"
          />
        ))}

        {/* core spine nodes */}
        <motion.g variants={nodeVariants}>
          <rect x="40" y="50" width="190" height="80" rx="4" fill="none" stroke={stroke} strokeWidth="1.25" />
          <text x="135" y="95" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="13" fill={fg} opacity="0.85">
            PERCEPTION
          </text>
        </motion.g>

        <motion.g variants={nodeVariants}>
          <rect
            x="355"
            y="35"
            width="190"
            height="110"
            rx="4"
            fill="hsl(var(--surface-inverted-foreground) / 0.1)"
            stroke={fg}
            strokeWidth="1.5"
          />
          <text x="450" y="83" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="13" fontWeight="600" fill={fg}>
            GROUNDING
          </text>
          <text x="450" y="102" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="13" fontWeight="600" fill={fg}>
            + GUARDRAIL
          </text>
        </motion.g>

        <motion.g variants={nodeVariants}>
          <rect x="670" y="50" width="190" height="80" rx="4" fill="none" stroke={stroke} strokeWidth="1.25" />
          <text x="765" y="95" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="13" fill={fg} opacity="0.85">
            GUIDANCE
          </text>
        </motion.g>

        {/* satellite nodes */}
        {SATELLITES.map((s) => (
          <motion.g key={s.label} variants={nodeVariants}>
            <rect
              x={s.cx - 75}
              y="340"
              width="150"
              height="56"
              rx="4"
              fill="none"
              stroke={stroke}
              strokeWidth="1"
              strokeDasharray="3 3"
            />
            <text x={s.cx} y="372" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="10.5" fill={fg} opacity="0.65">
              {s.label}
            </text>
          </motion.g>
        ))}

        {/* looping signal dot along the core spine — the one continuous
            motion in this diagram, skipped entirely under reduced motion */}
        {!prefersReducedMotion && (
          <motion.circle
            r="4"
            fill={fg}
            initial={{ cx: 230, cy: 90, opacity: 0 }}
            animate={{ cx: [230, 355, 545, 670], opacity: [0, 1, 1, 0] }}
            transition={{ duration: 4, repeat: Infinity, repeatDelay: 1, ease: "linear", delay: 1.4 }}
          />
        )}
      </motion.svg>
    </div>
  );
}
