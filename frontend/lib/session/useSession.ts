"use client";

import { useCallback, useRef, useState } from "react";

type SessionStatus = "idle" | "connecting" | "connected" | "error";

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

export function useSession(token: string | null) {
  const [status, setStatus] = useState<SessionStatus>("idle");
  const [captions, setCaptions] = useState<string[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

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
    socket.onclose = () => setStatus("idle");
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
