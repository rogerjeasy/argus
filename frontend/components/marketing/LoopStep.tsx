import type { LucideIcon } from "lucide-react";

export interface LoopStepData {
  step: number;
  icon: LucideIcon;
  title: string;
  description: string;
}

export function LoopStep({ step, icon: Icon, title, description }: LoopStepData) {
  return (
    <div className="flex flex-1 flex-col items-start gap-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
          {step}
        </span>
        <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
      </div>
      <h3 className="text-lg font-semibold tracking-tight">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
