import { ArrowRight, Layers } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Reveal } from "./Reveal";
import { AgentNode } from "./AgentNode";

const DOMAIN_TIERS = [
  { name: "Transit Navigation", tier: "Tier 1" },
  { name: "Personal Admin & Correspondence", tier: "Tier 1" },
  { name: "Indoor Wayfinding", tier: "Tier 2" },
  { name: "Retail & Checkout", tier: "Tier 3" },
  { name: "Dining & Ordering", tier: "Tier 3" },
  { name: "Document & Currency Reading", tier: "Tier 3" },
] as const;

export function ArchitectureSection() {
  return (
    <section id="architecture" aria-labelledby="architecture-heading" className="border-t border-border bg-secondary/40">
      <Reveal className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 id="architecture-heading" className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Eleven core agents. One plugin architecture.
          </h2>
          <p className="mt-4 text-pretty text-lg text-muted-foreground">
            Every domain reuses the same agent core. Only the domain plugin — its grounding source and, where
            applicable, its executors — changes.
          </p>
        </div>

        <div className="mx-auto mt-14 flex max-w-3xl flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <AgentNode label="Perception" />
          <ArrowRight className="h-5 w-5 shrink-0 rotate-90 text-muted-foreground sm:rotate-0" aria-hidden="true" />
          <AgentNode label="Grounding + Guardrail gate" emphasis />
          <ArrowRight className="h-5 w-5 shrink-0 rotate-90 text-muted-foreground sm:rotate-0" aria-hidden="true" />
          <AgentNode label="Guidance" />
        </div>
        <p className="mx-auto mt-4 max-w-md text-center text-pretty text-sm text-muted-foreground">
          Perception never talks directly to Guidance. Every fact reaches you through Grounding and Guardrail
          first — the rule that makes a hallucinated platform number, or a hallucinated call outcome,
          structurally hard, not just unlikely.
        </p>

        <div className="mx-auto mt-10 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-4">
          <AgentNode label="Memory" />
          <AgentNode label="Replanning" />
          <AgentNode label="Escalation" />
          <AgentNode label="Self-Calibration" />
        </div>

        <div className="mx-auto mt-16 flex max-w-3xl flex-wrap items-center justify-center gap-2">
          <span className="mr-1 inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
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
