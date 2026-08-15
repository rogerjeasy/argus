import "@testing-library/jest-dom";
import { vi } from "vitest";

// jsdom has no IntersectionObserver. Framer Motion's whileInView/useInView
// (used throughout the marketing page for scroll-triggered reveals) needs
// one to exist at all — and reports every observed element as immediately
// intersecting, so tests see the same "revealed" DOM a real scroll would
// eventually produce, deterministically, without waiting on real geometry.
class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null;
  readonly rootMargin: string = "";
  readonly thresholds: ReadonlyArray<number> = [];

  constructor(private callback: IntersectionObserverCallback) {}

  observe(target: Element) {
    const entry = {
      isIntersecting: true,
      target,
      boundingClientRect: target.getBoundingClientRect(),
      intersectionRatio: 1,
      intersectionRect: target.getBoundingClientRect(),
      rootBounds: null,
      time: Date.now(),
    } as IntersectionObserverEntry;
    this.callback([entry], this);
  }
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);

// Tests assert on final rendered content, not animation timing. Reporting
// prefers-reduced-motion as "on" makes every Framer Motion animation in
// the marketing components (stagger reveals, count-up, the looping
// signal dot, parallax) resolve to its end state synchronously instead of
// racing a real requestAnimationFrame clock — the same posture a real
// reduced-motion user gets, made the deterministic default for tests.
vi.stubGlobal(
  "matchMedia",
  vi.fn((query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
);
