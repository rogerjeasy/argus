"use client";

import { Bell, Mic, Vibrate } from "lucide-react";
import { Reveal } from "./Reveal";
import { ChannelCard } from "./ChannelCard";

export function MultimodalSection() {
  return (
    <section
      id="multimodal"
      aria-labelledby="multimodal-heading"
      className="border-t border-border bg-gradient-to-b from-primary/[0.07] via-primary/[0.02] to-transparent"
    >
      <Reveal className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 id="multimodal-heading" className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Three channels. Never decorative.
          </h2>
          <p className="mt-4 text-pretty text-lg text-muted-foreground">
            Voice, haptics, and sound are coordinated, task-triggered channels — not an app with a voice mode
            bolted on.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 sm:grid-cols-3">
          <ChannelCard
            icon={Mic}
            title="Voice, with barge-in"
            description="Bidirectional, real-time audio built on the Gemini Live API. Interrupt Argus mid-sentence, the way you'd interrupt a person."
          />
          <ChannelCard
            icon={Vibrate}
            title="Haptic compass"
            description="Distinct vibration patterns carry direction and urgency — no audio required, even in a loud station."
          />
          <ChannelCard
            icon={Bell}
            title="Audio earcons"
            description="Short, distinct tones for plan-updated, low-confidence, task-complete, and escalation — without constant verbal narration."
          />
        </div>

        <p className="mx-auto mt-10 max-w-2xl text-center text-pretty text-sm text-muted-foreground">
          Adaptive verbosity and pacing persist per user, and the same build speaks and listens in any
          language — including navigating an IVR or filling a form in a language other than the one you speak.
        </p>
      </Reveal>
    </section>
  );
}
