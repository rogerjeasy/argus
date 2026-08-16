"use client";

/**
 * Browser camera capture for Gemini Live's video realtime input.
 *
 * Unlike audio.ts's continuous PCM stream, this sends periodic JPEG
 * snapshots — matching how Gemini Live's video Blob input and the
 * backend's report_scene_observation tool are both designed to be used
 * (one observation per frame, not a continuous stream). See this task's
 * plan entry for why.
 */

/** How often a frame is captured and sent. Frequent enough for framing
 * feedback to feel responsive; infrequent enough not to flood the socket
 * or the Live session with more frames than a spoken response cadence
 * could ever keep up with. */
export const CAPTURE_INTERVAL_MS = 1500;

/** JPEG encode quality — smaller frames matter more than sharpness here;
 * this is a machine-read signage-OCR input, not a photo. */
const JPEG_QUALITY = 0.7;

export interface CameraCapture {
  /** Release the camera and stop capturing. */
  stop(): void;
}

/** Turn a `getUserMedia` rejection into something worth saying out loud. */
export function describeCameraError(error: unknown): string {
  const name = (error as { name?: string } | undefined)?.name;
  switch (name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Camera access was blocked. Allow the camera for this site in your browser settings, then start the session again.";
    case "NotFoundError":
    case "OverconstrainedError":
      return "No camera was found. Connect one and start the session again.";
    case "NotReadableError":
      return "The camera is in use by another app. Close it and start the session again.";
    default:
      return error instanceof Error && error.message
        ? `The camera could not be started: ${error.message}`
        : "The camera could not be started.";
  }
}

/**
 * Stream periodic JPEG camera frames until {@link CameraCapture.stop} is
 * called. Rejects if the user denies permission or no device exists —
 * callers are expected to surface that, not swallow it (matches
 * startMicrophoneCapture's contract in audio.ts).
 */
export async function startCameraCapture(onFrame: (jpeg: ArrayBuffer) => void): Promise<CameraCapture> {
  if (!navigator?.mediaDevices?.getUserMedia) {
    throw new Error("This browser does not support camera capture.");
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "environment" },
  });

  const videoEl = document.createElement("video");
  videoEl.srcObject = stream;
  videoEl.muted = true;
  await videoEl.play();

  const canvas = document.createElement("canvas");
  canvas.width = videoEl.videoWidth || 640;
  canvas.height = videoEl.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    stream.getTracks().forEach((track) => track.stop());
    throw new Error("This browser does not support canvas-based frame capture.");
  }

  let stopped = false;
  const intervalId = setInterval(() => {
    if (stopped) return;
    ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob || stopped) return;
        void blob.arrayBuffer().then((buffer) => {
          if (!stopped) onFrame(buffer);
        });
      },
      "image/jpeg",
      JPEG_QUALITY
    );
  }, CAPTURE_INTERVAL_MS);

  return {
    stop() {
      if (stopped) return;
      stopped = true;
      clearInterval(intervalId);
      stream.getTracks().forEach((track) => track.stop());
      videoEl.srcObject = null;
    },
  };
}
