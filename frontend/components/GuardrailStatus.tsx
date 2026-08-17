import { CheckCircle2, ShieldAlert, ShieldX } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import type { GuardrailDecisionValue } from "@/lib/session/protocol";

const CONFIG: Record<GuardrailDecisionValue, { icon: typeof CheckCircle2; tone: "success" | "warning" | "destructive"; label: string }> = {
  approved: { icon: CheckCircle2, tone: "success", label: "Approved" },
  requires_confirmation: { icon: ShieldAlert, tone: "warning", label: "Needs your confirmation" },
  requires_field_input: { icon: ShieldAlert, tone: "warning", label: "Needs one more detail" },
  denied: { icon: ShieldX, tone: "destructive", label: "Denied" },
};

export function GuardrailStatus({ decision }: { decision: GuardrailDecisionValue }) {
  const { icon, tone, label } = CONFIG[decision];
  return (
    <StatusBadge icon={icon} tone={tone}>
      {label}
    </StatusBadge>
  );
}
