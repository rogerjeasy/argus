import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const alertVariants = cva("relative w-full rounded-lg border px-4 py-3 text-sm [&>svg]:h-5 [&>svg]:w-5", {
  variants: {
    variant: {
      default: "border-border bg-card text-foreground",
      destructive: "border-destructive/40 bg-destructive/10 text-destructive",
    },
  },
  defaultVariants: { variant: "default" },
});

export type AlertProps = React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>;

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(({ className, variant, role = "alert", ...props }, ref) => (
  <div ref={ref} role={role} className={cn(alertVariants({ variant, className }))} {...props} />
));
Alert.displayName = "Alert";

export { Alert, alertVariants };
