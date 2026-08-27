"use client";

import { useCallback, useEffect, useState } from "react";
import { History } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useIdToken } from "@/lib/auth/useIdToken";
import { getHistory, type SessionHistoryEntry } from "@/lib/api/history";

type LoadState = "loading" | "loaded" | "error";

function formatWhen(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function HistoryPage() {
  const token = useIdToken();
  const [entries, setEntries] = useState<SessionHistoryEntry[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");

  const load = useCallback(() => {
    if (!token) return;
    setLoadState("loading");
    getHistory(token)
      .then((rows) => {
        setEntries(rows);
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

  if (loadState === "loading") {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (loadState === "error") {
    return (
      <Card>
        <CardContent className="items-center text-center">
          <p className="text-sm text-muted-foreground">Your history couldn&apos;t be loaded.</p>
          <Button variant="outline" onClick={load}>
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (entries.length === 0) {
    return (
      <Card>
        <CardContent className="items-center py-12 text-center">
          <History className="h-10 w-10 text-muted-foreground" aria-hidden />
          <h2 className="text-lg font-semibold tracking-tight text-foreground">No sessions logged yet</h2>
          <p className="max-w-sm text-sm text-muted-foreground">
            Once you have a conversation with Argus, a short record of it appears here.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {entries.map((entry) => (
        <li key={entry.session_id}>
          <Card>
            <CardContent className="gap-1 py-4">
              <p className="text-sm text-foreground">{entry.summary}</p>
              <p className="text-xs text-muted-foreground">{formatWhen(entry.started_at ?? entry.recorded_at)}</p>
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  );
}
