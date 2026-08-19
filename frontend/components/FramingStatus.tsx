import { CameraOff } from "lucide-react";
import { StatusCard } from "@/components/ui/status-card";

export function FramingStatus({ confidenceLow }: { confidenceLow: boolean }) {
  if (!confidenceLow) return null;
  return <StatusCard icon={CameraOff} tone="warning" label="Confidence low" detail="Reframe the camera" />;
}
