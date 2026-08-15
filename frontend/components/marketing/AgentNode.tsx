import { cn } from "@/lib/utils";

export function AgentNode({ label, emphasis }: { label: string; emphasis?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3 text-center text-sm font-medium shadow-sm",
        emphasis ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card text-foreground"
      )}
    >
      {label}
    </div>
  );
}
