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

  const { status, captions, start, stop } = useSession(token);
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
      <div aria-live="polite" className="min-h-[2rem] animate-in">
        {captions.map((line, index) => (
          <p key={index}>{line}</p>
        ))}
      </div>
    </div>
  );
}
