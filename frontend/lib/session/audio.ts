"use client";

/**
 * Browser audio for the Gemini Live round trip.
 *
 * Both directions carry raw, headerless, 16-bit signed little-endian PCM, mono
 * — the only format the Live API accepts on input and the only one it emits on
 * output. The two rates are deliberately different and are NOT
 * interchangeable:
 *
 *   - Capture (browser → Gemini) is 16 kHz. The backend declares exactly this
 *     to the API as `audio/pcm;rate=16000`; see `INPUT_SAMPLE_RATE` in
 *     `backend/app/ws/gemini_bridge.py`. Change one, change the other.
 *   - Playback (Gemini → browser) is 24 kHz. Decoding it at the capture rate
 *     plays the response back slow and low-pitched.
 */

/** Input rate Gemini Live expects. Mirrors the backend's INPUT_SAMPLE_RATE. */
export const CAPTURE_SAMPLE_RATE = 16000;

/** Rate Gemini Live emits its own audio at. */
export const PLAYBACK_SAMPLE_RATE = 24000;

/**
 * Frames per capture callback: ~256ms at 16 kHz. Large enough to keep the
 * WebSocket from being flooded with tiny frames, small enough that the
 * conversation still feels responsive.
 */
export const CAPTURE_BUFFER_SIZE = 4096;

type AudioContextConstructor = new (options?: AudioContextOptions) => AudioContext;

interface AudioContextCarrier {
  AudioContext?: AudioContextConstructor;
  webkitAudioContext?: AudioContextConstructor;
}

function resolveAudioContextConstructor(): AudioContextConstructor {
  const carrier = globalThis as unknown as AudioContextCarrier;
  const ctor = carrier.AudioContext ?? carrier.webkitAudioContext;
  if (!ctor) {
    throw new Error("This browser does not support the Web Audio API.");
  }
  return ctor;
}

/**
 * Convert Web Audio's Float32 samples (nominally -1..1) to the 16-bit signed
 * little-endian PCM Gemini Live expects.
 *
 * Values are clamped before scaling: a sample slightly outside the nominal
 * range is legal in Web Audio but would wrap around into loud noise once
 * truncated into an Int16.
 */
export function floatTo16BitPcm(input: Float32Array): ArrayBuffer {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i += 1) {
    const clamped = Math.max(-1, Math.min(1, input[i]));
    // Asymmetric scaling: Int16 spans -32768..32767, so -1 and +1 both map to
    // a representable value instead of overflowing at the positive end.
    output[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
  }
  return output.buffer;
}

/** Inverse of {@link floatTo16BitPcm}, for samples arriving from Gemini. */
export function pcm16ToFloat32(buffer: ArrayBuffer): Float32Array {
  // A trailing odd byte cannot form a sample; ignore it rather than reading
  // past the end of the buffer.
  const usableBytes = buffer.byteLength - (buffer.byteLength % 2);
  const view = new DataView(buffer, 0, usableBytes);
  const output = new Float32Array(usableBytes / 2);
  for (let i = 0; i < output.length; i += 1) {
    const sample = view.getInt16(i * 2, /* littleEndian */ true);
    output[i] = sample < 0 ? sample / 0x8000 : sample / 0x7fff;
  }
  return output;
}

/** Turn a `getUserMedia` rejection into something worth saying out loud. */
export function describeMicrophoneError(error: unknown): string {
  const name = (error as { name?: string } | undefined)?.name;
  switch (name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Microphone access was blocked. Allow the microphone for this site in your browser settings, then start the session again.";
    case "NotFoundError":
    case "OverconstrainedError":
      return "No microphone was found. Connect one and start the session again.";
    case "NotReadableError":
      return "The microphone is in use by another app. Close it and start the session again.";
    default:
      return error instanceof Error && error.message
        ? `The microphone could not be started: ${error.message}`
        : "The microphone could not be started.";
  }
}

export interface MicrophoneCapture {
  /** Release the microphone, the audio graph, and the capture context. */
  stop(): void;
}

/**
 * Stream microphone audio as 16 kHz PCM chunks until {@link
 * MicrophoneCapture.stop} is called.
 *
 * Rejects if the user denies permission or no device exists — callers are
 * expected to surface that, not swallow it.
 *
 * Implementation note (deliberate Phase 0 tradeoff): capture runs on a
 * `ScriptProcessorNode`. It is deprecated in favour of `AudioWorkletNode`, but
 * a worklet needs its processor shipped as a separately-fetched module, which
 * buys nothing at this phase's "relay the bytes, do nothing smart" scope. The
 * cost is that conversion happens on the main thread, so heavy UI work could
 * cause dropouts. Phase 1 should migrate once there is real UI contending for
 * the main thread.
 */
export async function startMicrophoneCapture(
  onChunk: (chunk: ArrayBuffer) => void
): Promise<MicrophoneCapture> {
  if (!navigator?.mediaDevices?.getUserMedia) {
    throw new Error("This browser does not support microphone capture.");
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      sampleRate: CAPTURE_SAMPLE_RATE,
      echoCancellation: true,
      noiseSuppression: true,
    },
  });

  let context: AudioContext | null = null;
  try {
    const AudioContextCtor = resolveAudioContextConstructor();
    // Requesting the rate on the context, not just on the track constraints:
    // browsers routinely ignore a `sampleRate` constraint and hand back the
    // hardware's native 44.1/48 kHz. A context pinned to 16 kHz resamples the
    // stream for us, so what reaches `onChunk` is genuinely 16 kHz.
    context = new AudioContextCtor({ sampleRate: CAPTURE_SAMPLE_RATE });

    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(CAPTURE_BUFFER_SIZE, 1, 1);

    processor.onaudioprocess = (event: AudioProcessingEvent) => {
      onChunk(floatTo16BitPcm(event.inputBuffer.getChannelData(0)));
    };

    // A ScriptProcessorNode only runs while connected to a destination, but
    // routing the mic to the speakers would produce a feedback howl — the last
    // thing an audio-first assistive tool should do. The silent gain node in
    // between keeps the node scheduled while emitting nothing.
    const silentSink = context.createGain();
    silentSink.gain.value = 0;

    source.connect(processor);
    processor.connect(silentSink);
    silentSink.connect(context.destination);

    const capturingContext = context;
    let stopped = false;

    return {
      stop() {
        if (stopped) return;
        stopped = true;
        processor.onaudioprocess = null;
        processor.disconnect();
        silentSink.disconnect();
        source.disconnect();
        stream.getTracks().forEach((track) => track.stop());
        void capturingContext.close?.();
      },
    };
  } catch (error) {
    // Never leave the microphone indicator lit because our own graph setup
    // failed after permission was already granted.
    stream.getTracks().forEach((track) => track.stop());
    void context?.close?.();
    throw error;
  }
}

/**
 * Plays back the 24 kHz PCM chunks Gemini streams over the WebSocket.
 *
 * Chunks arrive faster than real time, so each one is scheduled to start where
 * the previous one ends rather than at "now" — playing them all immediately
 * would overlap them into noise.
 */
export class PcmPlayer {
  private context: AudioContext | null = null;
  private nextStartTime = 0;

  private ensureContext(): AudioContext {
    if (!this.context) {
      const AudioContextCtor = resolveAudioContextConstructor();
      this.context = new AudioContextCtor({ sampleRate: PLAYBACK_SAMPLE_RATE });
      this.nextStartTime = 0;
    }
    // Browsers start a context suspended unless it was created during a user
    // gesture; the session's Start button qualifies, but resuming defensively
    // costs nothing and covers the autoplay-policy edge cases.
    if (this.context.state === "suspended") {
      void this.context.resume?.();
    }
    return this.context;
  }

  play(chunk: ArrayBuffer): void {
    const samples = pcm16ToFloat32(chunk);
    if (samples.length === 0) return;

    const context = this.ensureContext();
    const buffer = context.createBuffer(1, samples.length, PLAYBACK_SAMPLE_RATE);
    buffer.getChannelData(0).set(samples);

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);

    const startAt = Math.max(context.currentTime, this.nextStartTime);
    source.start(startAt);
    // Computed from the sample count rather than read off the AudioBuffer so
    // scheduling stays correct regardless of how the buffer reports itself.
    this.nextStartTime = startAt + samples.length / PLAYBACK_SAMPLE_RATE;
  }

  close(): void {
    const context = this.context;
    this.context = null;
    this.nextStartTime = 0;
    void context?.close?.();
  }
}
