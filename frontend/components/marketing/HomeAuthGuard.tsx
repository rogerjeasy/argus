"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthProvider";

/**
 * Wraps the public marketing homepage. Never blocks or delays the
 * marketing content's first paint — it only redirects a signed-in visitor
 * to /app once Firebase auth state has resolved, so a logged-out visitor
 * (the overwhelming majority of first-time traffic, including every judge)
 * sees the homepage instantly with no flash or layout shift.
 */
export function HomeAuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/app");
    }
  }, [loading, user, router]);

  return <>{children}</>;
}
