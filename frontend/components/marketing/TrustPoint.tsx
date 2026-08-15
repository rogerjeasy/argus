import type { LucideIcon } from "lucide-react";

export function TrustPoint({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="group flex items-start gap-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary transition-shadow duration-300 group-hover:shadow-[0_0_0_6px_hsl(var(--primary)/0.12)]">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <div>
        <h3 className="text-balance text-base font-semibold tracking-tight">{title}</h3>
        <p className="mt-1 text-pretty text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
