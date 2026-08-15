"use client";

import { Button, type ButtonProps } from "@/components/ui/button";
import { GoogleIcon } from "./GoogleIcon";

export function GoogleSignInButton({ loading, children, ...props }: ButtonProps & { loading?: boolean }) {
  return (
    <Button type="button" variant="outline" size="lg" className="w-full gap-3" disabled={loading} {...props}>
      <GoogleIcon className="h-5 w-5" />
      {children}
    </Button>
  );
}
