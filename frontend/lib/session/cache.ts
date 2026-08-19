const STORAGE_KEY = "argus:cached-guidance";

export interface CachedGuidance {
  captionText: string | null;
  framingText: string | null;
  captionLanguage: string;
}

export function saveCachedGuidance(state: CachedGuidance): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Storage can legitimately fail (private browsing, quota) — losing the
    // cache is a degraded-mode-of-degraded-mode, not worth crashing over.
  }
}

export function loadCachedGuidance(): CachedGuidance | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return null;
    return JSON.parse(raw) as CachedGuidance;
  } catch {
    return null;
  }
}

export function clearCachedGuidance(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Same reasoning as saveCachedGuidance.
  }
}
