import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  CAPTURE_BUFFER_SIZE,
  CAPTURE_SAMPLE_RATE,
  PLAYBACK_SAMPLE_RATE,
  PcmPlayer,
  describeMicrophoneError,
  floatTo16BitPcm,
  pcm16ToFloat32,
  startMicrophoneCapture,
} from "../lib/session/audio";

/**
 * jsdom ships neither the Web Audio API nor getUserMedia, so the whole audio
 * graph is stubbed. These fakes record what the production code asked for —
 * the constraints, the context rate, the node wiring — because those are
 * exactly the details that decide whether real audio works in a real browser.
 */

class FakeAudioParam {
  value = 1;
}

class FakeAudioNode {
  connectedTo: unknown[] = [];
  disconnectCalls = 0;

  connect(target: unknown) {
    this.connectedTo.push(target);
    return target;
  }

  disconnect() {
    this.disconnectCalls += 1;
  }
}

class FakeScriptProcessor extends FakeAudioNode {
  onaudioprocess: ((event: unknown) => void) | null = null;

  constructor(
    public bufferSize: number,
    public inputChannels: number,
    public outputChannels: number
  ) {
    super();
  }

  /** Simulate the browser delivering one buffer of captured samples. */
  emit(samples: Float32Array) {
    this.onaudioprocess?.({
      inputBuffer: { getChannelData: () => samples },
    });
  }
}

class FakeGainNode extends FakeAudioNode {
  gain = new FakeAudioParam();
}

class FakeBufferSource extends FakeAudioNode {
  buffer: FakeAudioBuffer | null = null;
  startedAt: number | null = null;

  start(when: number) {
    this.startedAt = when;
  }
}

class FakeAudioBuffer {
  private readonly channel: Float32Array;

  constructor(
    public channels: number,
    public length: number,
    public sampleRate: number
  ) {
    this.channel = new Float32Array(length);
  }

  getChannelData() {
    return this.channel;
  }
}

class FakeAudioContext {
  static instances: FakeAudioContext[] = [];

  state = "running";
  currentTime = 0;
  destination = new FakeAudioNode();
  closed = false;
  resumeCalls = 0;
  sources: FakeBufferSource[] = [];
  processors: FakeScriptProcessor[] = [];
  gains: FakeGainNode[] = [];
  mediaStreamSources: { stream: unknown; node: FakeAudioNode }[] = [];

  constructor(public options?: { sampleRate?: number }) {
    FakeAudioContext.instances.push(this);
  }

  createMediaStreamSource(stream: unknown) {
    const node = new FakeAudioNode();
    this.mediaStreamSources.push({ stream, node });
    return node;
  }

  createScriptProcessor(bufferSize: number, input: number, output: number) {
    const node = new FakeScriptProcessor(bufferSize, input, output);
    this.processors.push(node);
    return node;
  }

  createGain() {
    const node = new FakeGainNode();
    this.gains.push(node);
    return node;
  }

  createBuffer(channels: number, length: number, sampleRate: number) {
    return new FakeAudioBuffer(channels, length, sampleRate);
  }

  createBufferSource() {
    const node = new FakeBufferSource();
    this.sources.push(node);
    return node;
  }

  resume() {
    this.resumeCalls += 1;
    this.state = "running";
    return Promise.resolve();
  }

  close() {
    this.closed = true;
    return Promise.resolve();
  }
}

class FakeMediaStreamTrack {
  stopped = false;
  stop() {
    this.stopped = true;
  }
}

class FakeMediaStream {
  tracks = [new FakeMediaStreamTrack()];
  getTracks() {
    return this.tracks;
  }
}

let getUserMedia: ReturnType<typeof vi.fn>;

beforeEach(() => {
  FakeAudioContext.instances = [];
  getUserMedia = vi.fn(async () => new FakeMediaStream());
  vi.stubGlobal("AudioContext", FakeAudioContext);
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PCM conversion", () => {
  it("round-trips samples through 16-bit PCM within quantisation error", () => {
    const original = new Float32Array([0, 0.5, -0.5, 0.999, -0.999]);
    const restored = pcm16ToFloat32(floatTo16BitPcm(original));

    expect(restored.length).toBe(original.length);
    original.forEach((sample, index) => {
      expect(restored[index]).toBeCloseTo(sample, 4);
    });
  });

  it("encodes little-endian, which is what Gemini Live expects", () => {
    // 0.5 * 0x7fff = 16383.5 -> 16383 = 0x3FFF, little-endian => FF 3F.
    const bytes = new Uint8Array(floatTo16BitPcm(new Float32Array([0.5])));
    expect(Array.from(bytes)).toEqual([0xff, 0x3f]);
  });

  it("clamps out-of-range samples instead of letting them wrap", () => {
    const encoded = new Int16Array(floatTo16BitPcm(new Float32Array([2, -2])));
    expect(encoded[0]).toBe(32767);
    expect(encoded[1]).toBe(-32768);
  });

  it("ignores a trailing odd byte rather than reading past the buffer", () => {
    expect(pcm16ToFloat32(new ArrayBuffer(5)).length).toBe(2);
    expect(pcm16ToFloat32(new ArrayBuffer(0)).length).toBe(0);
  });
});

describe("startMicrophoneCapture", () => {
  it("requests a mono 16 kHz microphone stream", async () => {
    await startMicrophoneCapture(() => {});

    expect(getUserMedia).toHaveBeenCalledWith({
      audio: expect.objectContaining({
        channelCount: 1,
        sampleRate: CAPTURE_SAMPLE_RATE,
      }),
    });
  });

  it("pins the capture AudioContext to the capture rate", async () => {
    await startMicrophoneCapture(() => {});

    // Track constraints alone are routinely ignored by browsers; the context
    // rate is what actually guarantees 16 kHz reaches the socket.
    expect(FakeAudioContext.instances[0].options).toEqual({
      sampleRate: CAPTURE_SAMPLE_RATE,
    });
    expect(FakeAudioContext.instances[0].processors[0].bufferSize).toBe(CAPTURE_BUFFER_SIZE);
  });

  it("emits captured frames as 16-bit PCM", async () => {
    const chunks: ArrayBuffer[] = [];
    await startMicrophoneCapture((chunk) => chunks.push(chunk));

    FakeAudioContext.instances[0].processors[0].emit(new Float32Array([0, 0.5, -0.5]));

    expect(chunks).toHaveLength(1);
    expect(chunks[0].byteLength).toBe(3 * 2);
    expect(Array.from(new Int16Array(chunks[0]))).toEqual([0, 16383, -16384]);
  });

  it("never routes the microphone to the speakers", async () => {
    await startMicrophoneCapture(() => {});
    const context = FakeAudioContext.instances[0];

    // Feedback howl protection: the processor must reach the destination only
    // through a zero-gain node, so the node keeps running while emitting
    // nothing audible.
    expect(context.gains[0].gain.value).toBe(0);
    expect(context.processors[0].connectedTo).toEqual([context.gains[0]]);
    expect(context.gains[0].connectedTo).toEqual([context.destination]);
  });

  it("releases the microphone and the context on stop()", async () => {
    const capture = await startMicrophoneCapture(() => {});
    const context = FakeAudioContext.instances[0];
    const stream = context.mediaStreamSources[0].stream as FakeMediaStream;

    capture.stop();

    expect(stream.getTracks().every((track) => track.stopped)).toBe(true);
    expect(context.closed).toBe(true);
    expect(context.processors[0].onaudioprocess).toBeNull();
  });

  it("stops emitting chunks after stop()", async () => {
    const chunks: ArrayBuffer[] = [];
    const capture = await startMicrophoneCapture((chunk) => chunks.push(chunk));
    const processor = FakeAudioContext.instances[0].processors[0];

    capture.stop();
    processor.emit(new Float32Array([0.25]));

    expect(chunks).toHaveLength(0);
  });

  it("propagates a permission rejection to the caller", async () => {
    const denied = Object.assign(new Error("Permission denied"), {
      name: "NotAllowedError",
    });
    getUserMedia.mockRejectedValueOnce(denied);

    await expect(startMicrophoneCapture(() => {})).rejects.toBe(denied);
  });

  it("releases an already-granted stream if graph setup then fails", async () => {
    const stream = new FakeMediaStream();
    getUserMedia.mockResolvedValueOnce(stream);
    vi.stubGlobal(
      "AudioContext",
      class {
        constructor() {
          throw new Error("no audio device");
        }
      }
    );

    await expect(startMicrophoneCapture(() => {})).rejects.toThrow("no audio device");
    expect(stream.getTracks().every((track) => track.stopped)).toBe(true);
  });
});

describe("describeMicrophoneError", () => {
  it("explains a denied permission in plain language with a way forward", () => {
    const message = describeMicrophoneError({ name: "NotAllowedError" });
    expect(message).toMatch(/blocked/i);
    expect(message).toMatch(/browser settings/i);
  });

  it("distinguishes a missing device from a denied one", () => {
    expect(describeMicrophoneError({ name: "NotFoundError" })).toMatch(/no microphone/i);
  });

  it("falls back to a usable message for an unknown failure", () => {
    expect(describeMicrophoneError(new Error("boom"))).toMatch(/boom/);
    expect(describeMicrophoneError(undefined)).toMatch(/could not be started/i);
  });
});

describe("PcmPlayer", () => {
  it("decodes a chunk at the 24 kHz Gemini output rate and plays it", () => {
    const player = new PcmPlayer();
    player.play(floatTo16BitPcm(new Float32Array([0.1, 0.2, 0.3])));

    const context = FakeAudioContext.instances[0];
    expect(context.options).toEqual({ sampleRate: PLAYBACK_SAMPLE_RATE });

    const source = context.sources[0];
    expect(source.buffer?.sampleRate).toBe(PLAYBACK_SAMPLE_RATE);
    expect(source.buffer?.length).toBe(3);
    expect(source.connectedTo).toEqual([context.destination]);
    expect(source.startedAt).toBe(0);
  });

  it("schedules consecutive chunks back to back instead of overlapping them", () => {
    const player = new PcmPlayer();
    const chunk = floatTo16BitPcm(new Float32Array(PLAYBACK_SAMPLE_RATE / 2)); // 0.5s

    player.play(chunk);
    player.play(chunk);

    const context = FakeAudioContext.instances[0];
    expect(context.sources[0].startedAt).toBe(0);
    expect(context.sources[1].startedAt).toBeCloseTo(0.5, 5);
  });

  it("never schedules a chunk in the past", () => {
    const player = new PcmPlayer();
    player.play(floatTo16BitPcm(new Float32Array([0.1])));

    // Playback fell behind — e.g. the tab was backgrounded between chunks.
    const context = FakeAudioContext.instances[0];
    context.currentTime = 10;
    player.play(floatTo16BitPcm(new Float32Array([0.1])));

    expect(context.sources[1].startedAt).toBe(10);
  });

  it("resumes a context suspended by the autoplay policy", () => {
    const player = new PcmPlayer();
    player.play(floatTo16BitPcm(new Float32Array([0.1])));

    const context = FakeAudioContext.instances[0];
    context.state = "suspended";
    player.play(floatTo16BitPcm(new Float32Array([0.1])));

    expect(context.resumeCalls).toBe(1);
  });

  it("ignores empty chunks without creating a context", () => {
    new PcmPlayer().play(new ArrayBuffer(0));
    expect(FakeAudioContext.instances).toHaveLength(0);
  });

  it("closes the context and restarts scheduling on close()", () => {
    const player = new PcmPlayer();
    player.play(floatTo16BitPcm(new Float32Array(PLAYBACK_SAMPLE_RATE)));
    const first = FakeAudioContext.instances[0];

    player.close();
    expect(first.closed).toBe(true);

    player.play(floatTo16BitPcm(new Float32Array([0.1])));
    expect(FakeAudioContext.instances).toHaveLength(2);
    expect(FakeAudioContext.instances[1].sources[0].startedAt).toBe(0);
  });
});
