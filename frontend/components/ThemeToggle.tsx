"use client";

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
  const current = (ORDER as readonly string[]).includes(theme ?? "") ? (theme as Theme) : "light";
  const Icon = ICONS[current];
  const next = ORDER[(ORDER.indexOf(current) + 1) % ORDER.length];

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(next)}
      aria-label={`${LABELS[current]} active. Switch to ${LABELS[next]}.`}
    >
      <Icon className="h-5 w-5" aria-hidden />
    </Button>
  );
}
