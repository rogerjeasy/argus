import { CloudOff } from "lucide-react";
import { StatusCard } from "@/components/ui/status-card";

export function DegradedConnectivityStatus({ usingCachedGuidance }: { usingCachedGuidance: boolean }) {
  if (!usingCachedGuidance) return null;
  return <StatusCard icon={CloudOff} tone="warning" label="Reduced confidence" detail="Showing cached guidance while reconnecting" />;
}
