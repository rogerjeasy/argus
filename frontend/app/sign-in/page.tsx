"use client";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function SignInPage() {
  const { signInWithGoogle, loading } = useAuth();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold">Sign in to Argus</h1>
      <Button onClick={() => void signInWithGoogle()} disabled={loading} size="lg">
        Sign in with Google
      </Button>
    </main>
  );
}
