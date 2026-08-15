// frontend/components/marketing/FlagshipSection.tsx
import { CheckCircle2 } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { PhoneMockup } from "./PhoneMockup";
import { CaptionFeed, type CaptionLine } from "./CaptionFeed";

export interface FlagshipSectionProps {
  eyebrow: string;
  title: string;
  description: string;
  provesLabel: string;
  lines: CaptionLine[];
  reverse?: boolean;
}

export function FlagshipSection({ eyebrow, title, description, provesLabel, lines, reverse }: FlagshipSectionProps) {
  const copy = (
    <div>
      <StatusBadge icon={CheckCircle2} tone="info">
        Tier 1 · proven live
      </StatusBadge>
      <p className="mt-4 text-sm font-medium uppercase tracking-wide text-primary">{eyebrow}</p>
      <h3 className="mt-2 text-balance text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h3>
      <p className="mt-4 text-pretty text-muted-foreground">{description}</p>
      <p className="mt-4 text-sm font-medium text-foreground text-pretty">Proves: {provesLabel}</p>
    </div>
  );

  const mockup = (
    <PhoneMockup>
      <CaptionFeed lines={lines} />
    </PhoneMockup>
  );

  return (
    <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2 lg:gap-16">
      {reverse ? (
        <>
          {mockup}
          {copy}
        </>
      ) : (
        <>
          {copy}
          {mockup}
        </>
      )}
    </div>
  );
}
