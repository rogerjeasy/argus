"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  PcmPlayer,
  describeMicrophoneError,
  startMicrophoneCapture,
  type MicrophoneCapture,
} from "./audio";
import { describeCameraError, startCameraCapture, type CameraCapture } from "./video";
import { parseControlFrame, parseFramingFrame, type GuidanceFrame } from "./protocol";

type SessionStatus = "idle" | "connecting" | "connected" | "error";

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

/** Client-to-server binary frames carry a 1-byte type prefix — must match
 * FRAME_TYPE_AUDIO/FRAME_TYPE_VIDEO in backend/app/ws/session.py exactly. */
const FRAME_TYPE_AUDIO = 1;
const FRAME_TYPE_VIDEO = 2;

/**
 * Owns one voice session: the authenticated WebSocket, the microphone feeding
 * it, and playback of whatever Gemini sends back.
 *
 * Server-to-client binary frames are raw PCM audio (see `lib/session/audio.ts`
 * for the rates). Client-to-server binary frames carry a 1-byte type prefix
 * (FRAME_TYPE_AUDIO below) — the socket is meant to carry a second frame kind
 * (camera frames) on top of audio, so every client-to-server frame says which
 * kind it is; see backend/app/ws/session.py's matching FRAME_TYPE_AUDIO/
 * FRAME_TYPE_VIDEO constants. Text frames carry one JSON control message —
 * the orchestrator's spoken guidance, captioned, alongside the Guardrail
 * decision that gated it (see `lib/session/protocol.ts`).
 */
export function useSession(token: string | null) {
  const [status, setStatus] = useState<SessionStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [captionText, setCaptionText] = useState<string | null>(null);
  const [guardrailDecision, setGuardrailDecision] = useState<GuidanceFrame["guardrailDecision"] | null>(null);
  const [framingText, setFramingText] = useState<string | null>(null);
  const [confidenceLow, setConfidenceLow] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const captureRef = useRef<MicrophoneCapture | null>(null);
  const cameraRef = useRef<CameraCapture | null>(null);
  const playerRef = useRef<PcmPlayer | null>(null);

  // Not a useCallback: the unmount effect below must not re-run when this
  // changes, and every caller is inside this hook anyway.
  const teardownRef = useRef<() => void>(() => {});
  teardownRef.current = () => {
    captureRef.current?.stop();
    captureRef.current = null;
    cameraRef.current?.stop();
    cameraRef.current = null;
    playerRef.current?.close();
    playerRef.current = null;
    // Null the ref *before* calling close(): a real WebSocket.close() never
    // re-enters onclose synchronously, but test doubles (and some
    // environments) do. Nulling first means a re-entrant call sees no socket
    // left to close instead of closing it a second time / recursing forever.
    const socket = socketRef.current;
    socketRef.current = null;
    socket?.close();
    // A stale caption/guardrail state from the ending session must not
    // bleed into the next one — this runs both on stop() and at the top of
    // start() (clearing out a previous unclean disconnect).
    setCaptionText(null);
    setGuardrailDecision(null);
    setFramingText(null);
    setConfidenceLow(false);
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
          const prefixed = new Uint8Array(chunk.byteLength + 1);
          prefixed[0] = FRAME_TYPE_AUDIO;
          prefixed.set(new Uint8Array(chunk), 1);
          socket.send(prefixed.buffer);
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

  const beginCameraCapture = useCallback(async (socket: WebSocket) => {
    try {
      const camera = await startCameraCapture((jpeg) => {
        if (socket.readyState === WebSocket.OPEN) {
          const prefixed = new Uint8Array(jpeg.byteLength + 1);
          prefixed[0] = FRAME_TYPE_VIDEO;
          prefixed.set(new Uint8Array(jpeg), 1);
          socket.send(prefixed.buffer);
        }
      });
      if (socketRef.current !== socket) {
        camera.stop();
        return;
      }
      cameraRef.current = camera;
    } catch (error) {
      // Camera is a secondary channel — audio-only degraded mode is still a
      // working session, so a camera failure logs and continues rather than
      // tearing down the whole session the way a microphone failure does.
      console.error(describeCameraError(error));
    }
  }, []);

  const start = useCallback(async () => {
    if (!token) {
      setStatus("error");
      setErrorMessage("You need to be signed in before starting a session.");
      return;
    }

    // Starting again while a previous session's socket/mic/player are still
    // around (e.g. clicking Start after an unclean disconnect) must not
    // silently orphan them — each leaked AudioContext counts against the
    // browser's per-page cap until new ones can no longer be created.
    teardownRef.current();

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
      void beginCameraCapture(socket);
    };
    socket.onerror = () => {
      setStatus("error");
      setErrorMessage("The connection to Argus failed. Check your network and try again.");
      // An error on the socket means this session is dead: release the mic
      // and audio contexts now rather than waiting for onclose. A server- or
      // network-initiated end is the most likely real-world disconnect — far
      // more likely than a clean, user-clicked Stop — so this is the path
      // that most needs the same cleanup start()/stop() already guarantee.
      teardownRef.current();
    };
    // A real disconnect fires onclose immediately after onerror; without this
    // guard the "Connection error" status — the one thing ConnectionStatus is
    // mandated to surface via icon+text+color — would be overwritten by
    // "Not connected" before anyone could perceive it.
    socket.onclose = () => {
      setStatus((prev) => (prev === "error" ? "error" : "idle"));
      // Also reached on a clean server-initiated close (no preceding
      // onerror) — same reasoning as above: don't leave the mic live with
      // no session behind it. teardownRef is reentrancy-safe (nulls its
      // refs before closing anything), so a second call here after onerror
      // already ran is a harmless no-op.
      teardownRef.current();
    };
    socket.onmessage = (event: MessageEvent) => {
      if (event.data instanceof ArrayBuffer) {
        playerRef.current?.play(event.data);
        return;
      }
      if (typeof event.data === "string") {
        const framingFrame = parseFramingFrame(event.data);
        if (framingFrame) {
          setFramingText(framingFrame.text);
          setConfidenceLow(framingFrame.confidenceLow);
          return;
        }
        const frame = parseControlFrame(event.data);
        if (frame) {
          setCaptionText(frame.text);
          setGuardrailDecision(frame.guardrailDecision);
        }
        // A malformed/unrecognized frame is dropped rather than announced:
        // pushing raw protocol noise into the live region would read it
        // aloud to a screen reader.
      }
    };
  }, [token, beginCapture, beginCameraCapture]);

  const stop = useCallback(() => {
    teardownRef.current();
    setStatus("idle");
    setErrorMessage(null);
  }, []);

  return { status, errorMessage, captionText, guardrailDecision, framingText, confidenceLow, start, stop };
}
