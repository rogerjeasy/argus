import { apiFetch } from "./client";

export interface SessionHistoryEntry {
  session_id: string;
  summary: string;
  started_at: string | null;
  ended_at: string | null;
  recorded_at: string | null;
}

export async function getHistory(token: string): Promise<SessionHistoryEntry[]> {
  return apiFetch<SessionHistoryEntry[]>("/api/history", { token });
}
