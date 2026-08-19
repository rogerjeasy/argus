import type { ReactNode } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AuthBrandPanel } from "./AuthBrandPanel";

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen w-full bg-background">
      <AuthBrandPanel />
      <main className="relative flex w-full flex-1 items-center justify-center px-4 py-12 sm:px-6 lg:w-1/2 lg:px-16">
        {/* A visitor can land here directly (a bookmark, a link from email)
            without ever passing through the marketing nav or the /app
            shell — both of which already have a theme toggle. Someone who
            needs high-contrast needs it here first, not after signing in. */}
        <div className="absolute right-4 top-4 sm:right-6 sm:top-6">
          <ThemeToggle />
        </div>
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  );
}
