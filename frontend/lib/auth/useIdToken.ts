"use client";

import { useEffect, useState } from "react";
import { useAuth } from "./AuthProvider";

/**
 * Fetches a fresh Firebase ID token whenever the signed-in user changes.
 * Returns null while signed out or before the first token resolves.
 */
export function useIdToken(): string | null {
  const { user } = useAuth();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setToken(null);
      return;
    }
    let cancelled = false;
    void user
      .getIdToken()
      .then((next) => {
        if (!cancelled) setToken(next);
      })
      .catch((err) => {
        console.error(err);
        if (!cancelled) setToken(null);
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  return token;
}
