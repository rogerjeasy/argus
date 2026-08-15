import type { LucideIcon } from "lucide-react";

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
    <div className="flex flex-col items-start gap-4 rounded-xl border border-border bg-card p-6 shadow-sm">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <h3 className="text-balance text-lg font-semibold tracking-tight">{title}</h3>
      <p className="text-pretty text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
