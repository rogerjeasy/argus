import { apiFetch } from "./client";

export interface UserSettings {
  verbosity: "terse" | "normal" | "verbose";
  pace: "slow" | "normal" | "fast";
  audio_perception_enabled: boolean;
  language_preference: string;
}

export async function getUserSettings(token: string): Promise<UserSettings> {
  return apiFetch<UserSettings>("/api/settings", { token });
}

export async function updateUserSettings(
  token: string,
  update: Partial<UserSettings>
): Promise<UserSettings> {
  return apiFetch<UserSettings>("/api/settings", {
    method: "PUT",
    token,
    body: JSON.stringify(update),
  });
}
