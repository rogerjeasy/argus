"use client";

import { useAuth } from "@/lib/auth/AuthProvider";
import { SessionControl } from "@/components/SessionControl";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function HomePage() {
  const { user, loading } = useAuth();

  if (loading) {
    return <main>Loading…</main>;
  }

  if (!user) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p>
          <a href="/sign-in">Sign in</a> to start a session.
        </p>
        <ThemeToggle />
      </main>
    );
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
