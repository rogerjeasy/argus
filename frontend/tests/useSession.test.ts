import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useSession } from "../lib/session/useSession";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: unknown }) => void) | null = null;
  sent: unknown[] = [];

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(data: unknown) {
    this.sent.push(data);
  }

  close() {
    this.onclose?.();
  }
}

describe("useSession", () => {
  it("transitions idle -> connecting -> connected when the socket opens", async () => {
    vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
    const { result } = renderHook(() => useSession("fake-token"));

    expect(result.current.status).toBe("idle");

    await act(async () => {
      await result.current.start();
    });
    expect(result.current.status).toBe("connecting");

    act(() => {
      FakeWebSocket.instances.at(-1)?.onopen?.();
    });
    await waitFor(() => expect(result.current.status).toBe("connected"));
  });

  it("stop() closes the socket and returns to idle", async () => {
    vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
    const { result } = renderHook(() => useSession("fake-token"));

    await act(async () => {
      await result.current.start();
    });
    act(() => {
      FakeWebSocket.instances.at(-1)?.onopen?.();
    });
    await waitFor(() => expect(result.current.status).toBe("connected"));

    act(() => {
      result.current.stop();
    });
    expect(result.current.status).toBe("idle");
  });
});
