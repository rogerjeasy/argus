"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useSession } from "@/lib/session/useSession";
import { Button } from "@/components/ui/button";
import { ConnectionStatus } from "./ConnectionStatus";
import { FramingStatus } from "./FramingStatus";
import { GuardrailStatus } from "./GuardrailStatus";

export function SessionControl() {
  const { user } = useAuth();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setToken(null);
      return;
    }
    void user
      .getIdToken()
      .then(setToken)
      .catch((err) => {
        console.error(err);
        setToken(null);
      });
  }, [user]);

  const { status, errorMessage, captionText, guardrailDecision, framingText, confidenceLow, start, stop } =
    useSession(token);
  const isActive = status === "connected" || status === "connecting";

  return (
    <div className="flex flex-col gap-4">
      <Button
        onClick={() => void (isActive ? stop() : start())}
        disabled={!token}
        variant={isActive ? "destructive" : "default"}
        size="lg"
      >
        {isActive ? "Stop" : "Start"}
      </Button>
      <ConnectionStatus status={status} />
      {guardrailDecision ? <GuardrailStatus decision={guardrailDecision} /> : null}
      <FramingStatus confidenceLow={confidenceLow} />
      {/* Captions: what Argus actually said, shown alongside the audio —
          never color/audio alone as the only channel for a guardrail-relevant
          reply. `polite` because it updates routinely, not something the
          user must act on. */}
      <div aria-live="polite" className="min-h-[2rem]">
        {captionText ? <p>{captionText}</p> : null}
      </div>
      {/* Camera framing guidance ("move slightly right", etc.) — a separate
          region from captionText since the two update independently and on
          different cadences (spoken plan guidance vs. periodic camera
          feedback). `polite` for the same reason captionText is. */}
      <div aria-live="polite" className="min-h-[1.5rem]">
        {framingText ? <p>{framingText}</p> : null}
      </div>
      {/* This region exists for what audio cannot convey: why a session
          failed, in plain language, announced without stealing focus.
          `assertive` because it only ever holds something the user must act
          on. */}
      <div aria-live="assertive" className="min-h-[2rem] animate-in">
        {errorMessage ? <p>{errorMessage}</p> : null}
      </div>
    </div>
  );
}
