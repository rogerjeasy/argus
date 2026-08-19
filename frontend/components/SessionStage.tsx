"use client";

import { AlertTriangle, CloudOff, Mic, ShieldAlert, Volume2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { deriveStageState, type StageState, type StageStateInput } from "@/lib/session/stageState";

const STAGE_CONFIG: Record<StageState, { icon: LucideIcon | null; toneClass: string; label: string }> = {
  idle: { icon: null, toneClass: "bg-muted text-muted-foreground", label: "Ready to start" },
  connecting: { icon: null, toneClass: "bg-primary/15 text-primary", label: "Connecting…" },
  listening: { icon: Mic, toneClass: "bg-primary/15 text-primary", label: "Listening" },
  speaking: { icon: Volume2, toneClass: "bg-accent/15 text-accent", label: "Argus is speaking" },
  "guardrail-pending": { icon: ShieldAlert, toneClass: "bg-warning/15 text-warning", label: "Needs your input" },
  degraded: { icon: CloudOff, toneClass: "bg-muted text-muted-foreground", label: "Reduced connectivity" },
  error: { icon: AlertTriangle, toneClass: "bg-destructive/15 text-destructive", label: "Something went wrong" },
};

export interface SessionStageProps extends StageStateInput {
  micLevel: number;
  playbackLevel: number;
}

export function SessionStage({ micLevel, playbackLevel, ...stateInput }: SessionStageProps) {
  // stateInput is missing playbackLevel (destructured out above) — StageStateInput
  // requires it, so it's added back explicitly rather than passing stateInput as-is.
  const stageState = deriveStageState({ ...stateInput, playbackLevel });
  const { icon: Icon, toneClass, label } = STAGE_CONFIG[stageState];
  const isListening = stageState === "listening";
  const isSpeaking = stageState === "speaking";
  const activeLevel = isSpeaking ? playbackLevel : isListening ? micLevel : 0;
  const scale = 1 + activeLevel * 0.15;

  return (
    // role="status" wraps both the circle and its caption, not the circle
    // alone — matching StatusBadge/StatusCard's own convention of announcing
    // icon and visible text together, rather than relying on an aria-label
    // some screen readers won't reliably re-announce on its own.
    <div role="status" className="flex flex-col items-center gap-3" data-stage-state={stageState}>
      <div
        className={cn(
          "flex h-40 w-40 items-center justify-center rounded-full border-2 transition-transform duration-150 ease-out sm:h-60 sm:w-60",
          toneClass,
          stageState === "degraded" ? "border-dashed border-muted-foreground/50" : "border-transparent",
          stageState === "idle" && "animate-stage-breathe",
          stageState === "connecting" && "animate-pulse"
        )}
        style={isListening || isSpeaking ? { transform: `scale(${scale})` } : undefined}
      >
        {Icon ? <Icon className="h-14 w-14" aria-hidden /> : null}
      </div>
      <p className="text-base font-medium text-foreground">{label}</p>
    </div>
  );
}
