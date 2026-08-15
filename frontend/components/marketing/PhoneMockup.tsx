import { cn } from "@/lib/utils";

export function PhoneMockup({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "mx-auto w-full max-w-[300px] rounded-[2rem] border border-border bg-card p-3 shadow-md",
        className
      )}
    >
      <div className="flex items-center justify-center pb-2" aria-hidden="true">
        <span className="h-1.5 w-10 rounded-full bg-muted-foreground/30" />
      </div>
      <div className="min-h-[280px] rounded-2xl bg-background p-4">{children}</div>
    </div>
  );
}
