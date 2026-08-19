"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  PcmPlayer,
  describeMicrophoneError,
  startMicrophoneCapture,
  type MicrophoneCapture,
} from "./audio";
import { describeCameraError, startCameraCapture, type CameraCapture } from "./video";
import {
  parseControlFrame, parseFramingFrame, sendResolveConfirmation, sendResolveFieldInput, type GuidanceFrame,
} from "./protocol";
import { RECONNECT_MAX_ATTEMPTS, reconnectDelayMs } from "./reconnect";
import { loadCachedGuidance, saveCachedGuidance } from "./cache";

type SessionStatus = "idle" | "connecting" | "connected" | "reconnecting" | "error";

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
  const [pendingConfirmation, setPendingConfirmation] = useState<{ stepId: string; text: string } | null>(null);
  const [pendingFieldRequest, setPendingFieldRequest] = useState<{ stepId: string; text: string; label: string } | null>(null);
  const [usingCachedGuidance, setUsingCachedGuidance] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const captureRef = useRef<MicrophoneCapture | null>(null);
  const cameraRef = useRef<CameraCapture | null>(null);
  const playerRef = useRef<PcmPlayer | null>(null);
  const reconnectAttemptRef = useRef(0);
  const intentionalCloseRef = useRef(false);
  const reachedConnectedRef = useRef(false);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Not a useCallback: the unmount effect below must not re-run when this
  // changes, and every caller is inside this hook anyway.
  const teardownRef = useRef<() => void>(() => {});
  teardownRef.current = () => {
    if (reconnectTimeoutRef.current !== null) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setUsingCachedGuidance(false);
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
    setPendingConfirmation(null);
    setPendingFieldRequest(null);
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
    if (captureRef.current) return; // already capturing — a reconnect's onopen must not start a second stream
    try {
      const capture = await startMicrophoneCapture((chunk) => {
        // Checked against socketRef.current, not the socket this call
        // started with: after a reconnect, socketRef.current points at the
        // new live socket while this closure's own `socket` parameter
        // would forever point at the old, permanently-closed one — audio
        // would never resume sending after a reconnect otherwise.
        const current = socketRef.current;
        if (current && current.readyState === WebSocket.OPEN) {
          const prefixed = new Uint8Array(chunk.byteLength + 1);
          prefixed[0] = FRAME_TYPE_AUDIO;
          prefixed.set(new Uint8Array(chunk), 1);
          current.send(prefixed.buffer);
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
    if (cameraRef.current) return; // same idempotency reasoning as beginCapture
    try {
      const camera = await startCameraCapture((jpeg) => {
        const current = socketRef.current;
        if (current && current.readyState === WebSocket.OPEN) {
          const prefixed = new Uint8Array(jpeg.byteLength + 1);
          prefixed[0] = FRAME_TYPE_VIDEO;
          prefixed.set(new Uint8Array(jpeg), 1);
          current.send(prefixed.buffer);
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

  const establishConnection = useCallback((currentToken: string) => {
    const socket = new WebSocket(`${WS_BASE_URL}/ws/session?token=${currentToken}`);
    // ArrayBuffer rather than the default Blob: playback needs synchronous
    // access to the bytes, and Blob would force an async round trip per frame.
    socket.binaryType = "arraybuffer";
    socketRef.current = socket;
    if (!playerRef.current) playerRef.current = new PcmPlayer();

    socket.onopen = () => {
      setStatus("connected");
      reachedConnectedRef.current = true;
      reconnectAttemptRef.current = 0;
      void beginCapture(socket);
      void beginCameraCapture(socket);
    };
    socket.onerror = () => {
      setStatus("error");
      setErrorMessage("The connection to Argus failed. Check your network and try again.");
      // An error on the socket means this session is dead: release the mic
      // and audio contexts now rather than waiting for onclose. Unlike a
      // clean onclose (below), an error never triggers a reconnect attempt
      // — it's treated as more severe, matching this codebase's existing
      // distinction between "server closed us cleanly" and "something is
      // actually wrong with the connection."
      teardownRef.current();
    };
    // A real disconnect fires onclose immediately after onerror; without this
    // guard the "Connection error" status — the one thing ConnectionStatus is
    // mandated to surface via icon+text+color — would be overwritten before
    // anyone could perceive it.
    socket.onclose = () => {
      // A real WebSocket.close() never re-enters onclose synchronously,
      // but this codebase's own test double does (see teardownRef's own
      // comment on the same reentrancy) — and teardownRef's fallback path
      // below calls itself, which calls socket.close(), which would
      // re-enter this exact handler on the now-already-nulled socketRef.
      // Bailing here when this event no longer concerns the current
      // socket stops that from scheduling a second, spurious reconnect
      // (or double-executing the fallback) on every close.
      if (socketRef.current !== socket) return;
      if (intentionalCloseRef.current) {
        setStatus("idle");
        teardownRef.current();
        return;
      }
      // A clean onclose (no preceding onerror), after having been
      // connected at least once, is the most likely real disconnect in
      // production — Gemini dropping the stream, a token expiring, a
      // Cloud Run instance recycling, a short network gap. Reconnect
      // instead of tearing down, replaying the last-known guidance from
      // local storage in the meantime (design doc §6).
      if (reachedConnectedRef.current && reconnectAttemptRef.current < RECONNECT_MAX_ATTEMPTS) {
        const cached = loadCachedGuidance();
        if (cached) {
          setCaptionText(cached.captionText);
          setFramingText(cached.framingText);
          setUsingCachedGuidance(true);
        }
        setStatus("reconnecting");
        reconnectAttemptRef.current += 1;
        const delay = reconnectDelayMs(reconnectAttemptRef.current);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectTimeoutRef.current = null;
          establishConnection(currentToken);
        }, delay);
        return;
      }
      // Exhausted the retry budget, or never reached "connected" in the
      // first place (today's original behavior for a failed initial
      // connect) — fall back to full teardown.
      setStatus((prev) => (prev === "error" ? "error" : "idle"));
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
          setUsingCachedGuidance(false);
          return;
        }
        const frame = parseControlFrame(event.data);
        if (frame) {
          setCaptionText(frame.text);
          setGuardrailDecision(frame.guardrailDecision);
          setUsingCachedGuidance(false);
          // Framing text is deliberately not cached — see this task's plan
          // note on why stale camera guidance would be actively misleading
          // in a way stale spoken guidance is not.
          saveCachedGuidance({ captionText: frame.text, framingText: null });
          setPendingConfirmation(
            frame.guardrailDecision === "requires_confirmation" ? { stepId: frame.stepId, text: frame.text } : null
          );
          setPendingFieldRequest(
            frame.guardrailDecision === "requires_field_input"
              ? { stepId: frame.stepId, text: frame.text, label: frame.fieldLabel ?? "value" }
              : null
          );
        }
        // A malformed/unrecognized frame is dropped rather than announced:
        // pushing raw protocol noise into the live region would read it
        // aloud to a screen reader.
      }
    };
  }, [beginCapture, beginCameraCapture]);

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
    intentionalCloseRef.current = false;
    reachedConnectedRef.current = false;
    reconnectAttemptRef.current = 0;

    setStatus("connecting");
    setErrorMessage(null);
    playerRef.current = new PcmPlayer();
    establishConnection(token);
  }, [token, establishConnection]);

  const stop = useCallback(() => {
    intentionalCloseRef.current = true;
    teardownRef.current();
    setStatus("idle");
    setErrorMessage(null);
  }, []);

  const resolveConfirmation = useCallback((accepted: boolean) => {
    const socket = socketRef.current;
    const pending = pendingConfirmation;
    if (socket && pending) {
      sendResolveConfirmation(socket, pending.stepId, accepted);
      setPendingConfirmation(null);
    }
  }, [pendingConfirmation]);

  const resolveFieldInput = useCallback((value: string) => {
    const socket = socketRef.current;
    const pending = pendingFieldRequest;
    if (socket && pending) {
      sendResolveFieldInput(socket, pending.stepId, value);
      setPendingFieldRequest(null);
    }
  }, [pendingFieldRequest]);

  return {
    status, errorMessage, captionText, guardrailDecision, framingText, confidenceLow, usingCachedGuidance,
    pendingConfirmation, resolveConfirmation, pendingFieldRequest, resolveFieldInput, start, stop,
  };
}
