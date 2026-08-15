import { cn } from "@/lib/utils";

export interface CaptionLine {
  speaker: "argus" | "user";
  text: string;
  live?: boolean;
}

export function CaptionFeed({ lines }: { lines: CaptionLine[] }) {
  return (
    <ol aria-label="Live caption transcript" className="flex flex-col gap-3">
      {lines.map((line, index) => (
        <li
          key={index}
          className={cn(
            "flex flex-col gap-1 rounded-xl px-3 py-2 text-sm leading-snug",
            line.speaker === "argus" ? "bg-primary/10 text-foreground" : "self-end bg-secondary text-foreground"
          )}
        >
          <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            {line.speaker === "argus" ? "Argus" : "You"}
            {line.live && (
              <span className="inline-flex items-center gap-1 text-accent">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" aria-hidden="true" />
                live
              </span>
            )}
          </span>
          <span>{line.text}</span>
        </li>
      ))}
    </ol>
  );
}
