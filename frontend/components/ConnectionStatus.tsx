import { AlertTriangle, Loader2, Wifi, WifiOff } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";

const CONFIG = {
  idle: { icon: WifiOff, tone: "neutral" as const, label: "Not connected" },
  connecting: { icon: Loader2, tone: "info" as const, label: "Connecting…" },
  connected: { icon: Wifi, tone: "success" as const, label: "Connected" },
  error: { icon: AlertTriangle, tone: "destructive" as const, label: "Connection error" },
};

export function ConnectionStatus({ status }: { status: keyof typeof CONFIG }) {
  const { icon, tone, label } = CONFIG[status];
  return (
    <StatusBadge icon={icon} tone={tone}>
      {label}
    </StatusBadge>
  );
}
