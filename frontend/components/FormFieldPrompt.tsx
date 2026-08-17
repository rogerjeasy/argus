"use client";

import { useState, type FormEvent } from "react";

import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface FormFieldPromptProps {
  stepId: string;
  text: string;
  label: string;
  onResolve: (value: string) => void;
}

/**
 * The visual half of Form-Filling's one-missing-field ask (design doc §11).
 * A real accessible input — label, helper text — alongside the spoken
 * question, so a sighted companion can type it if speech recognition
 * struggles with something like a policy number. Submitting here resolves
 * the exact same pending field a spoken answer does; both call
 * resolveFieldInput() from useSession(), never two competing paths.
 *
 * `<form>` gets real submit semantics (Enter submits, not just the button)
 * without adding its own box in the layout — `className="contents"` keeps
 * its children as direct flex items of DialogContent's own flex column, the
 * same gap-6 rhythm ConfirmationPrompt uses.
 */
export function FormFieldPrompt({ stepId, text, label, onResolve }: FormFieldPromptProps) {
  const [value, setValue] = useState("");
  const descriptionId = `form-field-description-${stepId}`;
  const inputId = `form-field-input-${stepId}`;
  const trimmed = value.trim();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (trimmed.length > 0) {
      onResolve(trimmed);
    }
  };

  return (
    <Dialog open onOpenChange={() => {}}>
      <DialogContent aria-describedby={descriptionId}>
        <form className="contents" onSubmit={submit}>
          <DialogTitle>One more thing</DialogTitle>
          <DialogDescription id={descriptionId}>{text}</DialogDescription>
          <div className="flex flex-col gap-2">
            <Label htmlFor={inputId}>{label}</Label>
            <Input
              id={inputId}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              autoFocus
              autoComplete="off"
            />
          </div>
          <Button type="submit" variant="default" disabled={trimmed.length === 0}>
            Submit
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
