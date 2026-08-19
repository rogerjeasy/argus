"use client";

import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth/AuthProvider";
import { getUserSettings, updateUserSettings } from "@/lib/api/userSettings";

/**
 * The one settings control this phase needs — audio perception's opt-in
 * toggle, the first setting in this product carrying real privacy weight
 * (design doc §5, §8). Deliberately minimal: this is not a general
 * settings page backfilling verbosity/pace's own UI (Phase 0 scope, not
 * this one's to fix) — see this task's plan note.
 */
export function SettingsPanel() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!open || !user) return;
    let cancelled = false;
    (async () => {
      const token = await user.getIdToken();
      const settings = await getUserSettings(token);
      if (!cancelled) {
        setEnabled(settings.audio_perception_enabled);
        setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, user]);

  const handleToggle = async (next: boolean) => {
    setEnabled(next); // optimistic — the control must feel instant
    if (!user) return;
    const token = await user.getIdToken();
    await updateUserSettings(token, { audio_perception_enabled: next });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          Settings
        </Button>
      </DialogTrigger>
      <DialogContent aria-describedby="audio-perception-description">
        <DialogTitle>Settings</DialogTitle>
        <DialogDescription id="audio-perception-description">
          Audio perception continuously listens for concerning ambient sounds — like an alarm
          or a knock — while a session is active, even when you&apos;re not actively giving a
          command. It never records or stores audio, and always requires a second independent
          signal before ever contacting anyone on your behalf. Off by default.
        </DialogDescription>
        <div className="flex items-center justify-between gap-4">
          <Label htmlFor="audio-perception-toggle">Audio perception</Label>
          <Switch
            id="audio-perception-toggle"
            checked={loaded ? enabled : false}
            onCheckedChange={handleToggle}
            aria-label="Audio perception"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
