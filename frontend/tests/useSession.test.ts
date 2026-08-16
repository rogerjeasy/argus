import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSession } from "../lib/session/useSession";

// The audio graph itself is exercised against fake Web Audio APIs in
// audio.test.ts. Here it is mocked so these tests can be about the *wiring*:
// that the mic is started when the socket opens, that its frames reach the
// socket, that inbound frames reach playback, and that a refusal is surfaced.
const { startMicrophoneCapture, play, close, capturedOnChunk, stopCapture } = vi.hoisted(() => ({
  startMicrophoneCapture: vi.fn(),
  play: vi.fn(),
  close: vi.fn(),
  stopCapture: vi.fn(),
  capturedOnChunk: { current: null as ((chunk: ArrayBuffer) => void) | null },
}));

vi.mock("../lib/session/audio", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/session/audio")>();
  return {
    ...actual,
    startMicrophoneCapture,
    PcmPlayer: class {
      play = play;
      close = close;
    },
  };
});

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static OPEN = 1;
  static CLOSED = 3;

  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: unknown }) => void) | null = null;
  sent: unknown[] = [];
  readyState = FakeWebSocket.OPEN;
  binaryType = "blob";
  closeCalls = 0;

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(data: unknown) {
    this.sent.push(data);
  }

  close() {
    this.closeCalls += 1;
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.();
  }
}

function latestSocket(): FakeWebSocket {
  const socket = FakeWebSocket.instances.at(-1);
  if (!socket) throw new Error("no socket was opened");
  return socket;
}

/** Start a session and drive the socket to open, as a real browser would. */
async function startAndOpen(result: { current: ReturnType<typeof useSession> }) {
  await act(async () => {
    await result.current.start();
  });
  await act(async () => {
    latestSocket().onopen?.();
  });
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  capturedOnChunk.current = null;
  startMicrophoneCapture.mockReset();
  startMicrophoneCapture.mockImplementation(async (onChunk: (chunk: ArrayBuffer) => void) => {
    capturedOnChunk.current = onChunk;
    return { stop: stopCapture };
  });
  play.mockReset();
  close.mockReset();
  stopCapture.mockReset();
  vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useSession connection lifecycle", () => {
  it("transitions idle -> connecting -> connected when the socket opens", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    expect(result.current.status).toBe("idle");

    await act(async () => {
      await result.current.start();
    });
    expect(result.current.status).toBe("connecting");

    await act(async () => {
      latestSocket().onopen?.();
    });
    await waitFor(() => expect(result.current.status).toBe("connected"));
  });

  it("requests binary frames as ArrayBuffers", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);

    // Blob would force an async read per audio frame before playback.
    expect(latestSocket().binaryType).toBe("arraybuffer");
  });

  it("stop() closes the socket, releases the mic, and returns to idle", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);
    await waitFor(() => expect(result.current.status).toBe("connected"));
    const socket = latestSocket();

    act(() => {
      result.current.stop();
    });

    expect(result.current.status).toBe("idle");
    expect(socket.closeCalls).toBe(1);
    expect(stopCapture).toHaveBeenCalled();
    expect(close).toHaveBeenCalled();
  });

  it("preserves the error status when onclose fires right after onerror", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await act(async () => {
      await result.current.start();
    });
    const socket = latestSocket();

    act(() => {
      socket.onerror?.();
    });
    await waitFor(() => expect(result.current.status).toBe("error"));

    act(() => {
      socket.onclose?.();
    });
    expect(result.current.status).toBe("error");
    expect(result.current.errorMessage).toMatch(/connection/i);
  });

  it("reports a missing token instead of opening a socket", async () => {
    const { result } = renderHook(() => useSession(null));

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.status).toBe("error");
    expect(result.current.errorMessage).toMatch(/signed in/i);
    expect(FakeWebSocket.instances).toHaveLength(0);
  });

  it("releases the microphone when the component unmounts mid-session", async () => {
    const { result, unmount } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);

    unmount();

    expect(stopCapture).toHaveBeenCalled();
    expect(close).toHaveBeenCalled();
    expect(latestSocket().closeCalls).toBe(1);
  });

  it("releases the microphone when the server closes the socket (no prior error)", async () => {
    // The most likely real disconnect in production — Gemini dropping the
    // stream, a token expiring, a Cloud Run instance recycling — arrives as
    // a clean onclose with no preceding onerror. A live mic indicator with
    // no session behind it is exactly the failure this test guards against.
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);
    await waitFor(() => expect(capturedOnChunk.current).not.toBeNull());
    const socket = latestSocket();

    act(() => {
      socket.onclose?.();
    });

    expect(result.current.status).toBe("idle");
    expect(stopCapture).toHaveBeenCalled();
    expect(close).toHaveBeenCalled();
  });

  it("releases the microphone when the socket errors", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);
    await waitFor(() => expect(capturedOnChunk.current).not.toBeNull());
    const socket = latestSocket();

    act(() => {
      socket.onerror?.();
    });

    expect(result.current.status).toBe("error");
    expect(stopCapture).toHaveBeenCalled();
    expect(close).toHaveBeenCalled();
  });

  it("tears down a stale capture/player/socket before starting a new session", async () => {
    // Clicking Start again after an unclean disconnect (rather than a fresh
    // mount) must not silently orphan the previous mic capture and audio
    // contexts — each leaked AudioContext counts against the browser's
    // per-page cap until new ones can no longer be created.
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);
    // Wait for beginCapture's internal await to resolve and populate
    // captureRef, not just for "connected" status (which is set
    // synchronously in onopen, before beginCapture's promise settles).
    await waitFor(() => expect(capturedOnChunk.current).not.toBeNull());
    const firstSocket = latestSocket();

    await act(async () => {
      await result.current.start();
    });

    expect(firstSocket.closeCalls).toBe(1);
    expect(stopCapture).toHaveBeenCalled();
    expect(close).toHaveBeenCalled();
    expect(FakeWebSocket.instances).toHaveLength(2);
  });
});

describe("useSession microphone capture", () => {
  it("starts capturing only once the socket is open", async () => {
    const { result } = renderHook(() => useSession("fake-token"));

    await act(async () => {
      await result.current.start();
    });
    expect(startMicrophoneCapture).not.toHaveBeenCalled();

    await act(async () => {
      latestSocket().onopen?.();
    });
    await waitFor(() => expect(startMicrophoneCapture).toHaveBeenCalledTimes(1));
  });

  it("sends each captured PCM chunk over the socket", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);
    await waitFor(() => expect(capturedOnChunk.current).not.toBeNull());

    const chunk = new Int16Array([1, -1, 32767]).buffer;
    act(() => {
      capturedOnChunk.current?.(chunk);
    });

    expect(latestSocket().sent).toEqual([chunk]);
  });

  it("drops captured chunks once the socket is no longer open", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);
    await waitFor(() => expect(capturedOnChunk.current).not.toBeNull());
    const socket = latestSocket();
    const onChunk = capturedOnChunk.current;

    act(() => {
      result.current.stop();
    });
    act(() => {
      onChunk?.(new ArrayBuffer(4));
    });

    // Sending on a closing socket throws; a late capture callback must not
    // take the session down with it.
    expect(socket.sent).toHaveLength(0);
  });

  it("surfaces a denied microphone as an error status, not a stuck session", async () => {
    startMicrophoneCapture.mockRejectedValueOnce(
      Object.assign(new Error("Permission denied"), { name: "NotAllowedError" })
    );

    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorMessage).toMatch(/blocked/i);
    // onclose must not quietly downgrade the error to "idle".
    expect(result.current.status).toBe("error");
  });

  it("does not leave the mic running if the session is stopped during the permission prompt", async () => {
    let resolveCapture: ((capture: { stop: () => void }) => void) | undefined;
    startMicrophoneCapture.mockReturnValueOnce(
      new Promise<{ stop: () => void }>((resolve) => {
        resolveCapture = resolve;
      })
    );

    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);

    act(() => {
      result.current.stop();
    });
    await act(async () => {
      resolveCapture?.({ stop: stopCapture });
    });

    expect(stopCapture).toHaveBeenCalled();
  });
});

describe("useSession playback", () => {
  it("plays a binary frame from the server", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);

    const audio = new Int16Array([100, -100]).buffer;
    act(() => {
      latestSocket().onmessage?.({ data: audio });
    });

    expect(play).toHaveBeenCalledWith(audio);
  });

  it("ignores non-binary frames rather than announcing protocol noise", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);

    // The old implementation pushed String(event.data) into an aria-live
    // region, which read "[object Blob]" aloud to a screen reader.
    act(() => {
      latestSocket().onmessage?.({ data: "unexpected text frame" });
    });

    expect(play).not.toHaveBeenCalled();
    expect(result.current.status).toBe("connected");
  });

  it("surfaces caption text and a guardrail decision from a guidance frame", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);

    act(() => {
      latestSocket().onmessage?.({
        data: JSON.stringify({
          type: "guidance",
          text: "Head to platform 4.",
          haptic_pattern: "pattern-forward",
          earcon: "earcon-plan-updated",
          guardrail_decision: "requires_confirmation",
        }),
      });
    });

    expect(result.current.captionText).toBe("Head to platform 4.");
    expect(result.current.guardrailDecision).toBe("requires_confirmation");
  });

  it("drops a malformed control frame without touching caption/guardrail state", async () => {
    const { result } = renderHook(() => useSession("fake-token"));
    await startAndOpen(result);

    act(() => {
      latestSocket().onmessage?.({ data: "unexpected text frame" });
    });

    expect(result.current.captionText).toBeNull();
    expect(result.current.guardrailDecision).toBeNull();
  });
});
