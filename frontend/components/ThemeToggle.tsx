"use client";

import { useEffect, useState } from "react";
import { Contrast, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

const ORDER = ["light", "dark", "high-contrast"] as const;
type Theme = (typeof ORDER)[number];
const ICONS: Record<Theme, typeof Sun> = { light: Sun, dark: Moon, "high-contrast": Contrast };
const LABELS: Record<Theme, string> = {
  light: "Light theme",
  dark: "Dark theme",
  "high-contrast": "High-contrast theme",
};

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  // The persisted theme lives in localStorage, which the server can't
  // read — so the server, and the client's very first render before this
  // effect runs, both have to render the same theme-agnostic placeholder.
  // Swapping to the real icon/label only after mount turns that swap into
  // an ordinary client update instead of a hydration mismatch.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const current = (ORDER as readonly string[]).includes(theme ?? "") ? (theme as Theme) : "light";
  const Icon = mounted ? ICONS[current] : Sun;
  const next = ORDER[(ORDER.indexOf(current) + 1) % ORDER.length];

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(next)}
      aria-label={mounted ? `${LABELS[current]} active. Switch to ${LABELS[next]}.` : "Toggle theme"}
    >
      <Icon className="h-5 w-5" aria-hidden />
    </Button>
  );
}
