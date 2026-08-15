"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Tracks whether an element has scrolled into the viewport, once. Drives a
 * one-shot fade + slide-up reveal per section instead of pulling in an
 * animation library.
 *
 * State starts false on both the server and the client's initial render —
 * evaluating IntersectionObserver's availability inside a useState
 * initializer would differ between the server (no such global) and the
 * client (a real browser has one), causing a hydration mismatch. The
 * availability check instead happens inside the client-only effect below.
 *
 * If IntersectionObserver isn't available (an older browser), content
 * flips to visible immediately in that same effect rather than staying
 * permanently hidden — the reveal is decorative, so the fallback is to
 * skip it, never to hide content no observer will ever reveal.
 */
export function useInView<T extends HTMLElement>(options?: IntersectionObserverInit) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || inView) return;

    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setInView(true);
        observer.disconnect();
      }
    }, options ?? { threshold: 0.15 });

    observer.observe(node);
    return () => observer.disconnect();
  }, [options]);

  return { ref, inView };
}
