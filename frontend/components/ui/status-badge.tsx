import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const statusBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-base font-medium",
  {
    variants: {
      tone: {
        neutral: "border-border bg-secondary text-secondary-foreground",
        success: "border-transparent bg-success text-success-foreground",
        warning: "border-transparent bg-warning text-warning-foreground",
        destructive: "border-transparent bg-destructive text-destructive-foreground",
        info: "border-transparent bg-info text-info-foreground",
      },
    },
    defaultVariants: { tone: "neutral" },
  }
);

export interface StatusBadgeProps extends VariantProps<typeof statusBadgeVariants> {
  icon: LucideIcon;
  children: React.ReactNode;
  className?: string;
}

export function StatusBadge({ icon: Icon, tone, children, className }: StatusBadgeProps) {
  return (
    <span className={cn(statusBadgeVariants({ tone, className }))} role="status">
      <Icon className="h-4 w-4" aria-hidden />
      <span>{children}</span>
    </span>
  );
}
