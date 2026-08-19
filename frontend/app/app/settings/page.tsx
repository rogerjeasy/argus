"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useIdToken } from "@/lib/auth/useIdToken";
import { getUserSettings, updateUserSettings, type UserSettings } from "@/lib/api/userSettings";

const DEFAULT_SETTINGS: UserSettings = {
  verbosity: "normal", pace: "normal", audio_perception_enabled: false, language_preference: "en",
};

type LoadState = "loading" | "loaded" | "error";

export default function SettingsPage() {
  const token = useIdToken();
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [loadState, setLoadState] = useState<LoadState>("loading");

  const load = useCallback(() => {
    if (!token) return;
    setLoadState("loading");
    getUserSettings(token)
      .then((next) => {
        setSettings(next);
        setLoadState("loaded");
      })
      .catch((err) => {
        console.error(err);
        setLoadState("error");
      });
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const patch = async (update: Partial<UserSettings>) => {
    setSettings((prev) => ({ ...prev, ...update })); // optimistic — matches audio-perception/language's existing pattern
    if (!token) return;
    await updateUserSettings(token, update);
  };

  if (loadState === "loading") {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (loadState === "error") {
    return (
      <Card>
        <CardContent className="items-center text-center">
          <p className="text-sm text-muted-foreground">Your settings couldn&apos;t be loaded.</p>
          <Button variant="outline" onClick={load}>
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Voice & guidance</CardTitle>
          <CardDescription>How much Argus says, and how quickly it says it.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-4">
            <Label htmlFor="verbosity-select">Verbosity</Label>
            <Select
              id="verbosity-select"
              value={settings.verbosity}
              onChange={(v) => patch({ verbosity: v as UserSettings["verbosity"] })}
              aria-label="Verbosity"
            >
              <option value="terse">Terse</option>
              <option value="normal">Normal</option>
              <option value="verbose">Verbose</option>
            </Select>
          </div>
          <div className="flex items-center justify-between gap-4">
            <Label htmlFor="pace-select">Pace</Label>
            <Select
              id="pace-select"
              value={settings.pace}
              onChange={(v) => patch({ pace: v as UserSettings["pace"] })}
              aria-label="Pace"
            >
              <option value="slow">Slow</option>
              <option value="normal">Normal</option>
              <option value="fast">Fast</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Language</CardTitle>
          <CardDescription>The language Argus speaks and captions its guidance in.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-4">
            <Label htmlFor="language-select">Language</Label>
            <Select
              id="language-select"
              value={settings.language_preference}
              onChange={(v) => patch({ language_preference: v })}
              aria-label="Language"
            >
              <option value="en">English</option>
              <option value="ar">Arabic</option>
              <option value="he">Hebrew</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Audio perception</CardTitle>
          <CardDescription>
            Continuously listens for concerning ambient sounds — like an alarm or a knock — while a
            session is active, even when you&apos;re not actively giving a command. It never records or
            stores audio, and always requires a second independent signal before ever contacting anyone
            on your behalf. Off by default.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-4">
            <Label htmlFor="audio-perception-toggle">Audio perception</Label>
            <Switch
              id="audio-perception-toggle"
              checked={settings.audio_perception_enabled}
              onCheckedChange={(next) => patch({ audio_perception_enabled: next })}
              aria-label="Audio perception"
            />
          </div>
        </CardContent>
      </Card>
      {/* Standing permissions intentionally has no section here: it is not a
          settings CRUD concept today — permissions are granted only through
          the in-session Self-Calibration confirmation-prompt flow, and no
          REST endpoint exists to read or manage them from a settings page. */}
    </div>
  );
}
