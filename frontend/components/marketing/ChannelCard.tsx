"use client";

import type { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";

export function ChannelCard({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="group flex flex-col items-start gap-4 rounded-xl border border-border bg-card p-6 shadow-sm hover:shadow-md"
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-shadow duration-300 group-hover:shadow-[0_0_0_6px_hsl(var(--primary)/0.12)]">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <h3 className="text-balance text-lg font-semibold tracking-tight">{title}</h3>
      <p className="text-pretty text-sm text-muted-foreground">{description}</p>
    </motion.div>
  );
}
