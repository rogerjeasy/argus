// frontend/components/marketing/FlagshipDomainsSection.tsx
import { Reveal } from "./Reveal";
import { FlagshipSection } from "./FlagshipSection";

export function FlagshipDomainsSection() {
  return (
    <section id="domains" aria-labelledby="domains-heading" className="border-t border-border bg-secondary/40">
      <Reveal className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 id="domains-heading" className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Two proofs. Two different halves of autonomy.
          </h2>
          <p className="mt-4 text-pretty text-lg text-muted-foreground">
            Spatial autonomy and transactional autonomy, each built to full, flawless, live-demo polish.
          </p>
        </div>

        <div className="mt-16 flex flex-col gap-20">
          <FlagshipSection
            eyebrow="Transit Navigation"
            title="A platform changes at the last minute. Argus catches it before you do."
            description="Argus grounds every step against a live real-time transit feed. When the live camera signage disagrees with the feed, that contradiction triggers an automatic replan — no one has to notice the problem and ask again."
            provesLabel="grounded planning and live replanning when reality contradicts the plan."
            lines={[
              { speaker: "argus", text: "Platform four, this way." },
              { speaker: "argus", text: "Platform changed to seven, confirmed.", live: true },
            ]}
          />
          <FlagshipSection
            eyebrow="Personal Admin & Correspondence"
            title="A pharmacy refill notice. A real phone call. A real answer."
            description="Argus reads the notice, reads back the step it wants to take, and waits for an explicit spoken yes before it ever places a real outbound call — then reports the structured outcome back in plain speech."
            provesLabel="autonomous execution of a real-world transaction, gated by an explicit confirmation."
            lines={[
              { speaker: "argus", text: "Call the pharmacy to confirm refill status?" },
              { speaker: "user", text: "Yes." },
              { speaker: "argus", text: "Refill confirmed, ready tomorrow, twelve dollar co-pay.", live: true },
            ]}
            reverse
          />
        </div>
      </Reveal>
    </section>
  );
}
