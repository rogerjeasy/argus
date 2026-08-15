import { Layers } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Reveal } from "./Reveal";
import { ArchitectureDiagram } from "./ArchitectureDiagram";

const DOMAIN_TIERS = [
  { name: "Transit Navigation", tier: "Tier 1" },
  { name: "Personal Admin & Correspondence", tier: "Tier 1" },
  { name: "Indoor Wayfinding", tier: "Tier 2" },
  { name: "Retail & Checkout", tier: "Tier 3" },
  { name: "Dining & Ordering", tier: "Tier 3" },
  { name: "Document & Currency Reading", tier: "Tier 3" },
] as const;

// The one dramatic anchor in the page's background rhythm (see the
// visual-refresh design doc §3) — full bg-surface-inverted band, the
// darkest section on the page regardless of light/dark app theme, so
// every piece of text and every SVG stroke here explicitly targets
// text-surface-inverted-foreground rather than the ambient foreground.
export function ArchitectureSection() {
  return (
    <section
      id="architecture"
      aria-labelledby="architecture-heading"
      className="border-y border-primary/20 bg-surface-inverted text-surface-inverted-foreground"
    >
      <Reveal className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 id="architecture-heading" className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Eleven core agents. One plugin architecture.
          </h2>
          <p className="mt-4 text-pretty text-lg text-surface-inverted-foreground/70">
            Every domain reuses the same agent core. Only the domain plugin — its grounding source and, where
            applicable, its executors — changes.
          </p>
        </div>

        <div className="mt-14">
          <ArchitectureDiagram />
        </div>

        <p className="mx-auto mt-8 max-w-md text-center text-pretty text-sm text-surface-inverted-foreground/70">
          Perception never talks directly to Guidance. Every fact reaches you through Grounding and Guardrail
          first — the rule that makes a hallucinated platform number, or a hallucinated call outcome,
          structurally hard, not just unlikely.
        </p>

        <div className="mx-auto mt-16 flex max-w-3xl flex-wrap items-center justify-center gap-2">
          <span className="mr-1 inline-flex items-center gap-1.5 text-sm font-medium text-surface-inverted-foreground/70">
            <Layers className="h-4 w-4" aria-hidden="true" />
            Six task domains, one contract:
          </span>
          {DOMAIN_TIERS.map((domain) => (
            <StatusBadge key={domain.name} icon={Layers} tone={domain.tier === "Tier 1" ? "success" : "neutral"}>
              {domain.name} · {domain.tier}
            </StatusBadge>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
