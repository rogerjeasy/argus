"use client";

import { useAuth } from "@/lib/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import { WatchingRings } from "./WatchingRings";
import { PhoneMockup } from "./PhoneMockup";
import { CaptionFeed } from "./CaptionFeed";

export function HeroSection() {
  const { signInWithGoogle, loading } = useAuth();

  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-12 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-2 lg:px-8 lg:py-32">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-primary">
            The agentic seeing-eye copilot
          </p>
          <h1 className="mt-4 text-balance text-5xl font-semibold tracking-tight sm:text-6xl lg:text-7xl">
            Argus doesn&apos;t describe the world. It acts in it.
          </h1>
          <p className="mt-6 max-w-xl text-pretty text-lg text-muted-foreground sm:text-xl">
            Say a goal out loud — reach your connecting train after a last-minute platform change, or resolve a
            pharmacy refill — and Argus perceives, plans, acts, and replans in real time until it&apos;s done.
          </p>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row">
            <Button size="lg" onClick={() => void signInWithGoogle()} disabled={loading}>
              Get started with Google
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href="#how-it-works">See how it works</a>
            </Button>
          </div>
        </div>

        <div className="relative mx-auto flex w-full max-w-sm items-center justify-center">
          <WatchingRings className="absolute h-[420px] w-[420px]" />
          <PhoneMockup className="relative">
            <CaptionFeed lines={[{ speaker: "argus", text: "Platform changed. This way instead.", live: true }]} />
          </PhoneMockup>
        </div>
      </div>
    </section>
  );
}
