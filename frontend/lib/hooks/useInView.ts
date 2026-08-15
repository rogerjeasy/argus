"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Tracks whether an element has scrolled into the viewport, once. Drives a
 * one-shot fade + slide-up reveal per section instead of pulling in an
 * animation library.
 *
 * If IntersectionObserver isn't available (an older browser, or a
 * non-browser render), content starts already visible rather than
 * permanently hidden — the reveal is decorative, so the fallback is to
 * skip it, never to hide content no observer will ever reveal.
 */
export function useInView<T extends HTMLElement>(options?: IntersectionObserverInit) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(() => typeof IntersectionObserver === "undefined");

  useEffect(() => {
    const node = ref.current;
    if (!node || inView || typeof IntersectionObserver === "undefined") return;

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
