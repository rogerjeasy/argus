"use client";

import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface ConfirmationPromptProps {
  stepId: string;
  text: string;
  onResolve: (accepted: boolean) => void;
}

/**
 * The visual half of Guardrail's spoken read-back-and-confirm gate (design
 * doc §11). Accept is always `variant="default"`, never `variant="destructive"`
 * regardless of stakes — that color stays reserved for genuinely
 * destructive/declining actions. A spoken "yes" resolves the exact same
 * pending step this dialog's Accept button does; both call the same
 * resolveConfirmation() from useSession(), never two competing paths.
 */
export function ConfirmationPrompt({ stepId, text, onResolve }: ConfirmationPromptProps) {
  return (
    <Dialog open onOpenChange={(open) => !open && onResolve(false)}>
      <DialogContent aria-describedby={`confirmation-${stepId}`}>
        <DialogTitle>Confirm this action</DialogTitle>
        <DialogDescription id={`confirmation-${stepId}`}>{text}</DialogDescription>
        <div className="flex gap-3">
          <Button variant="default" onClick={() => onResolve(true)}>
            Accept
          </Button>
          <Button variant="outline" onClick={() => onResolve(false)}>
            Decline
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
