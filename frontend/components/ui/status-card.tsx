import type { LucideIcon } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const statusCardIconVariants = cva("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", {
  variants: {
    tone: {
      neutral: "bg-secondary text-secondary-foreground",
      success: "bg-success/15 text-success",
      warning: "bg-warning/15 text-warning",
      destructive: "bg-destructive/15 text-destructive",
      info: "bg-info/15 text-info",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export interface StatusCardProps extends VariantProps<typeof statusCardIconVariants> {
  icon: LucideIcon;
  label: string;
  detail?: string;
  className?: string;
}

export function StatusCard({ icon: Icon, tone, label, detail, className }: StatusCardProps) {
  return (
    <div role="status" className={cn("flex items-center gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm", className)}>
      <div className={cn(statusCardIconVariants({ tone }))}>
        <Icon className="h-5 w-5" aria-hidden />
      </div>
      <div className="flex min-w-0 flex-col">
        <span className="truncate text-sm font-medium text-foreground">{label}</span>
        {detail ? <span className="truncate text-xs text-muted-foreground">{detail}</span> : null}
      </div>
    </div>
  );
}
