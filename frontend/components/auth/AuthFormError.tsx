import { AlertCircle } from "lucide-react";

import { Alert } from "@/components/ui/alert";

export function AuthFormError({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }
  return (
    <Alert variant="destructive" className="flex items-start gap-2.5">
      <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </Alert>
  );
}
