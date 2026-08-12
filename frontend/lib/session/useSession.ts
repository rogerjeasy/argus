"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  PcmPlayer,
  describeMicrophoneError,
  startMicrophoneCapture,
  type MicrophoneCapture,
} from "./audio";

type SessionStatus = "idle" | "connecting" | "connected" | "error";

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

/**
 * Owns one voice session: the authenticated WebSocket, the microphone feeding
 * it, and playback of whatever Gemini sends back.
 *
 * Phase 0's wire protocol is deliberately tiny — every binary frame in either
 * direction is raw PCM audio (see `lib/session/audio.ts` for the rates). There
 * is no text/caption frame type yet, so nothing here tries to render message
 * payloads as text.
 */
export function useSession(token: string | null) {
  const [status, setStatus] = useState<SessionStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const captureRef = useRef<MicrophoneCapture | null>(null);
  const playerRef = useRef<PcmPlayer | null>(null);

  // Not a useCallback: the unmount effect below must not re-run when this
  // changes, and every caller is inside this hook anyway.
  const teardownRef = useRef<() => void>(() => {});
  teardownRef.current = () => {
    captureRef.current?.stop();
    captureRef.current = null;
    playerRef.current?.close();
    playerRef.current = null;
    socketRef.current?.close();
    socketRef.current = null;
  };

  useEffect(() => {
    return () => {
      // Unmounting mid-session must release the microphone — a live mic
      // indicator with no session behind it is both a privacy problem and a
      // battery drain.
      teardownRef.current();
    };
  }, []);

  const beginCapture = useCallback(async (socket: WebSocket) => {
    try {
      const capture = await startMicrophoneCapture((chunk) => {
        // The socket can close between two capture callbacks; sending on a
        // closing socket throws.
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(chunk);
        }
      });
      // If the session was stopped while the permission prompt was open,
      // discard the capture we just started instead of leaking the mic.
      if (socketRef.current !== socket) {
        capture.stop();
        return;
      }
      captureRef.current = capture;
    } catch (error) {
      // Set the error status *before* closing the socket: onclose preserves an
      // existing error status but would otherwise reset us to "idle" and leave
      // the UI claiming everything is fine with no microphone attached.
      setStatus("error");
      setErrorMessage(describeMicrophoneError(error));
      teardownRef.current();
    }
  }, []);

  const start = useCallback(async () => {
    if (!token) {
      setStatus("error");
      setErrorMessage("You need to be signed in before starting a session.");
      return;
    }

    setStatus("connecting");
    setErrorMessage(null);

    const socket = new WebSocket(`${WS_BASE_URL}/ws/session?token=${token}`);
    // ArrayBuffer rather than the default Blob: playback needs synchronous
    // access to the bytes, and Blob would force an async round trip per frame.
    socket.binaryType = "arraybuffer";
    socketRef.current = socket;
    playerRef.current = new PcmPlayer();

    socket.onopen = () => {
      setStatus("connected");
      void beginCapture(socket);
    };
    socket.onerror = () => {
      setStatus("error");
      setErrorMessage("The connection to Argus failed. Check your network and try again.");
    };
    // A real disconnect fires onclose immediately after onerror; without this
    // guard the "Connection error" status — the one thing ConnectionStatus is
    // mandated to surface via icon+text+color — would be overwritten by
    // "Not connected" before anyone could perceive it.
    socket.onclose = () => setStatus((prev) => (prev === "error" ? "error" : "idle"));
    socket.onmessage = (event: MessageEvent) => {
      if (event.data instanceof ArrayBuffer) {
        playerRef.current?.play(event.data);
      }
      // Anything non-binary is unexpected in Phase 0 and is dropped rather
      // than announced: pushing an unknown payload into the live region would
      // read raw protocol noise to a screen reader.
    };
  }, [token, beginCapture]);

  const stop = useCallback(() => {
    teardownRef.current();
    setStatus("idle");
    setErrorMessage(null);
  }, []);

  return { status, errorMessage, start, stop };
}
