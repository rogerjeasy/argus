import { cn } from "@/lib/utils";

// Deliberately outside the project's rounded-lg/rounded-xl shape scale —
// a phone device frame needs a phone-like radius, not a card radius.
// A soft ambient shadow + subtle bezel gradient give it real device
// presence instead of reading as a flat wireframe rectangle.
export function PhoneMockup({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "mx-auto w-full max-w-[300px] rounded-[2rem] border border-border bg-gradient-to-b from-card to-muted p-3",
        "shadow-[0_2px_8px_hsl(var(--foreground)/0.04),0_24px_48px_-16px_hsl(var(--primary)/0.25)]",
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
