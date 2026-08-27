import type { Metadata } from "next";
import { History } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export const metadata: Metadata = { title: "History — Argus" };

export default function HistoryPage() {
  return (
    <Card>
      <CardContent className="items-center py-12 text-center">
        <History className="h-10 w-10 text-muted-foreground" aria-hidden />
        <h2 className="text-lg font-semibold tracking-tight text-foreground">No sessions logged yet</h2>
        <p className="max-w-sm text-sm text-muted-foreground">
          Once you start a session, a record of what Argus guided you through will appear here.
        </p>
      </CardContent>
    </Card>
  );
}
