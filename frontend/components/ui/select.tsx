import * as React from "react";

import { cn } from "@/lib/utils";

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "onChange"> {
  onChange: (value: string) => void;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(({ className, onChange, ...props }, ref) => {
  return (
    <select
      ref={ref}
      onChange={(event) => onChange(event.target.value)}
      className={cn(
        "flex h-11 w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-base text-foreground",
        "transition-colors duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  );
});
Select.displayName = "Select";

export { Select };
