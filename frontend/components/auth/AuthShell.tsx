import type { ReactNode } from "react";
import { AuthBrandPanel } from "./AuthBrandPanel";

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen w-full bg-background">
      <AuthBrandPanel />
      <main className="flex w-full flex-1 items-center justify-center px-4 py-12 sm:px-6 lg:w-1/2 lg:px-16">
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  );
}
