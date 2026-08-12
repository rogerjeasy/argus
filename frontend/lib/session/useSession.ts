"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type SessionStatus = "idle" | "connecting" | "connected" | "error";

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

export function useSession(token: string | null) {
  const [status, setStatus] = useState<SessionStatus>("idle");
  const [captions, setCaptions] = useState<string[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
    };
  }, []);

  const start = useCallback(async () => {
    if (!token) {
      setStatus("error");
      return;
    }
    setStatus("connecting");
    const socket = new WebSocket(`${WS_BASE_URL}/ws/session?token=${token}`);
    socketRef.current = socket;

    socket.onopen = () => setStatus("connected");
    socket.onerror = () => setStatus("error");
    // A real disconnect fires onclose immediately after onerror; without this
    // guard the "Connection error" status — the one thing ConnectionStatus is
    // mandated to surface via icon+text+color — would be overwritten by
    // "Not connected" before anyone could perceive it.
    socket.onclose = () => setStatus((prev) => (prev === "error" ? "error" : "idle"));
    socket.onmessage = (event) => {
      setCaptions((prev) => [...prev, String(event.data)]);
    };
  }, [token]);

  const stop = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;
    setStatus("idle");
  }, []);

  return { status, captions, start, stop };
}
