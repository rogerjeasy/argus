"use client";

import { useAuth } from "@/lib/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import { Reveal } from "./Reveal";
import { WatchingRings } from "./WatchingRings";

export function FinalCta() {
  const { signInWithGoogle, loading } = useAuth();

  return (
    <section className="relative overflow-hidden border-t border-primary/20 bg-gradient-to-br from-primary to-primary-deep text-surface-inverted-foreground">
      <Reveal className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-4 py-20 text-center sm:px-6 sm:py-28 lg:px-8">
        <WatchingRings rich className="h-28 w-28 text-surface-inverted-foreground opacity-90" />
        <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
          Give it a goal. Argus takes it from there.
        </h2>
        <Button
          size="lg"
          className="bg-surface-inverted-foreground text-surface-inverted hover:bg-surface-inverted-foreground/90"
          onClick={() => void signInWithGoogle()}
          disabled={loading}
        >
          Get started with Google
        </Button>
      </Reveal>
    </section>
  );
}
