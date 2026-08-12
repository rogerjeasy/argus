"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useSession } from "@/lib/session/useSession";
import { Button } from "@/components/ui/button";
import { ConnectionStatus } from "./ConnectionStatus";

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

  const { status, errorMessage, start, stop } = useSession(token);
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
      {/* Argus's reply is spoken, not captioned — Phase 0's protocol carries
          audio only. This region exists for what audio cannot convey: why a
          session failed, in plain language, announced without stealing focus.
          `assertive` because it only ever holds something the user must act
          on. */}
      <div aria-live="assertive" className="min-h-[2rem] animate-in">
        {errorMessage ? <p>{errorMessage}</p> : null}
      </div>
    </div>
  );
}
