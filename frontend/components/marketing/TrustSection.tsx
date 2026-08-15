import { EyeOff, KeyRound, Lock, ShieldCheck } from "lucide-react";
import { Reveal } from "./Reveal";
import { TrustPoint } from "./TrustPoint";

export function TrustSection() {
  return (
    <section id="trust" aria-labelledby="trust-heading" className="border-t border-border">
      <Reveal className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 id="trust-heading" className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Autonomy is earned, never assumed.
          </h2>
          <p className="mt-4 text-pretty text-lg text-muted-foreground">
            A camera pointed at the real world, and a task that can touch real money and real deadlines — this is
            core architecture, not an afterthought.
          </p>
        </div>

        <div className="mx-auto mt-14 grid max-w-4xl grid-cols-1 gap-x-10 gap-y-10 sm:grid-cols-2">
          <TrustPoint
            icon={EyeOff}
            title="No raw video, ever stored"
            description="Frames are processed ephemerally. Only structured, task-relevant signals cross into the rest of the system."
          />
          <TrustPoint
            icon={ShieldCheck}
            title="Tiered autonomy, never blanket autonomy"
            description="Routine, previously-approved actions proceed automatically. Anything financial, medical, or unprecedented always asks first."
          />
          <TrustPoint
            icon={Lock}
            title="Inbound content is untrusted"
            description="A scanned letter or live IVR audio is screened the same way a scraped web page would be — never treated as a standing permission."
          />
          <TrustPoint
            icon={KeyRound}
            title="Encrypted at rest"
            description="Medical- and financial-adjacent profile fields are encrypted specifically, on top of standard data protection."
          />
        </div>
      </Reveal>
    </section>
  );
}
