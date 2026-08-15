"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthProvider";
import { SessionControl } from "@/components/SessionControl";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function AppPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return <main className="flex min-h-screen items-center justify-center">Loading…</main>;
  }

  return (
    <main className="mx-auto max-w-2xl p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Argus</h1>
        <ThemeToggle />
      </div>
      <div className="mt-6">
        <SessionControl />
      </div>
    </main>
  );
}
