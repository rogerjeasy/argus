import { CheckCircle2, ShieldAlert, ShieldX } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import type { GuardrailDecisionValue } from "@/lib/session/protocol";

const CONFIG = {
  approved: { icon: CheckCircle2, tone: "success" as const, label: "Approved" },
  requires_confirmation: { icon: ShieldAlert, tone: "warning" as const, label: "Needs your confirmation" },
  denied: { icon: ShieldX, tone: "destructive" as const, label: "Denied" },
};

export function GuardrailStatus({ decision }: { decision: GuardrailDecisionValue }) {
  const { icon, tone, label } = CONFIG[decision];
  return (
    <StatusBadge icon={icon} tone={tone}>
      {label}
    </StatusBadge>
  );
}
