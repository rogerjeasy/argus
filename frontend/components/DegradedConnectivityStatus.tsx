import { CloudOff } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";

export function DegradedConnectivityStatus({ usingCachedGuidance }: { usingCachedGuidance: boolean }) {
  if (!usingCachedGuidance) return null;
  return (
    <StatusBadge icon={CloudOff} tone="warning">
      Reduced confidence — showing cached guidance while reconnecting
    </StatusBadge>
  );
}
