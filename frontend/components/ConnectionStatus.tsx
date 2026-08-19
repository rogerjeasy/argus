import { AlertTriangle, Loader2, RefreshCw, Wifi, WifiOff } from "lucide-react";
import { StatusCard } from "@/components/ui/status-card";

const CONFIG = {
  idle: { icon: WifiOff, tone: "neutral" as const, label: "Not connected" },
  connecting: { icon: Loader2, tone: "info" as const, label: "Connecting…" },
  reconnecting: { icon: RefreshCw, tone: "warning" as const, label: "Reconnecting…" },
  connected: { icon: Wifi, tone: "success" as const, label: "Connected" },
  error: { icon: AlertTriangle, tone: "destructive" as const, label: "Connection error" },
};

export function ConnectionStatus({ status }: { status: keyof typeof CONFIG }) {
  const { icon, tone, label } = CONFIG[status];
  return <StatusCard icon={icon} tone={tone} label={label} />;
}
