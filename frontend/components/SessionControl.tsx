"use client";

import { useIdToken } from "@/lib/auth/useIdToken";
import { useSession } from "@/lib/session/useSession";
import { Button } from "@/components/ui/button";
import { SessionStage } from "@/components/SessionStage";
import { TranscriptFeed } from "@/components/TranscriptFeed";
import { ConfirmationPrompt } from "./ConfirmationPrompt";
import { ConnectionStatus } from "./ConnectionStatus";
import { DegradedConnectivityStatus } from "./DegradedConnectivityStatus";
import { FormFieldPrompt } from "./FormFieldPrompt";
import { FramingStatus } from "./FramingStatus";
import { GuardrailStatus } from "./GuardrailStatus";

export function SessionControl() {
  const token = useIdToken();
  const {
    status, errorMessage, guardrailDecision, framingText, confidenceLow, usingCachedGuidance,
    micLevel, playbackLevel, transcriptHistory, pendingConfirmation, resolveConfirmation,
    pendingFieldRequest, resolveFieldInput, start, stop,
  } = useSession(token);
  const isActive = status === "connected" || status === "connecting";

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center gap-6">
      <SessionStage
        status={status}
        guardrailDecision={guardrailDecision}
        usingCachedGuidance={usingCachedGuidance}
        micLevel={micLevel}
        playbackLevel={playbackLevel}
      />

      <Button
        onClick={() => void (isActive ? stop() : start())}
        disabled={!token}
        variant={isActive ? "destructive" : "default"}
        size="lg"
      >
        {isActive ? "Stop session" : "Start session"}
      </Button>

      <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
        <ConnectionStatus status={status} />
        {guardrailDecision ? <GuardrailStatus decision={guardrailDecision} /> : null}
        <FramingStatus confidenceLow={confidenceLow} />
        <DegradedConnectivityStatus usingCachedGuidance={usingCachedGuidance} />
      </div>

      <div className="w-full">
        <TranscriptFeed entries={transcriptHistory} />
      </div>

      {/* Camera framing guidance ("move slightly right", etc.) — a separate
          region from the transcript since the two update independently and
          on different cadences (spoken plan guidance vs. periodic camera
          feedback). `polite` for the same reason TranscriptFeed's region is.
          The old standalone captionText paragraph that used to sit here is
          removed — TranscriptFeed's own aria-live region now carries that
          announcement role, without the visual duplication. */}
      <div aria-live="polite" className="min-h-[1.5rem] w-full text-center text-sm text-muted-foreground">
        {framingText ? <p>{framingText}</p> : null}
      </div>

      {/* This region exists for what audio cannot convey: why a session
          failed, in plain language, announced without stealing focus.
          `assertive` because it only ever holds something the user must act
          on. */}
      <div aria-live="assertive" className="min-h-[2rem] w-full animate-in text-center text-sm text-destructive">
        {errorMessage ? <p>{errorMessage}</p> : null}
      </div>

      {pendingConfirmation ? (
        <ConfirmationPrompt stepId={pendingConfirmation.stepId} text={pendingConfirmation.text} onResolve={resolveConfirmation} />
      ) : null}
      {pendingFieldRequest ? (
        <FormFieldPrompt
          stepId={pendingFieldRequest.stepId}
          text={pendingFieldRequest.text}
          label={pendingFieldRequest.label}
          onResolve={resolveFieldInput}
        />
      ) : null}
    </div>
  );
}
