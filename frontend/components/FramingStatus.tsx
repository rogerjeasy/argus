import { CameraOff } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";

export function FramingStatus({ confidenceLow }: { confidenceLow: boolean }) {
  if (!confidenceLow) return null;
  return (
    <StatusBadge icon={CameraOff} tone="warning">
      Confidence low — reframe the camera
    </StatusBadge>
  );
}
