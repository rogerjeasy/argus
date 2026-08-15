import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useInView } from "../lib/hooks/useInView";

let observedCallback: IntersectionObserverCallback | null = null;
const disconnect = vi.fn();
const observe = vi.fn();

class MockIntersectionObserver {
  constructor(callback: IntersectionObserverCallback) {
    observedCallback = callback;
  }
  observe = observe;
  disconnect = disconnect;
  unobserve = vi.fn();
  takeRecords = vi.fn(() => []);
  root = null;
  rootMargin = "";
  thresholds: number[] = [];
}

function Probe() {
  const { ref, inView } = useInView<HTMLDivElement>();
  return (
    <div ref={ref} data-testid="probe">
      {inView ? "visible" : "hidden"}
    </div>
  );
}

describe("useInView", () => {
  beforeEach(() => {
    observedCallback = null;
    disconnect.mockReset();
    observe.mockReset();
    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("starts hidden and flips to visible once the element intersects, then disconnects", () => {
    render(<Probe />);
    expect(screen.getByTestId("probe").textContent).toBe("hidden");
    expect(observe).toHaveBeenCalled();

    act(() => {
      observedCallback?.([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver);
    });

    expect(screen.getByTestId("probe").textContent).toBe("visible");
    expect(disconnect).toHaveBeenCalledTimes(1);
  });

  it("stays visible and never re-observes once it has already flipped", () => {
    render(<Probe />);
    act(() => {
      observedCallback?.([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver);
    });
    const observeCallsAfterFirstFlip = observe.mock.calls.length;

    act(() => {
      observedCallback?.([{ isIntersecting: false } as IntersectionObserverEntry], {} as IntersectionObserver);
    });

    expect(screen.getByTestId("probe").textContent).toBe("visible");
    expect(observe.mock.calls.length).toBe(observeCallsAfterFirstFlip);
  });
});
