import { Eye, Map, Navigation, RefreshCw, Target } from "lucide-react";
import { Reveal } from "./Reveal";
import { LoopStep, type LoopStepData } from "./LoopStep";

const STEPS: LoopStepData[] = [
  {
    step: 1,
    icon: Target,
    title: "Goal",
    description: "You state one intent in natural speech — no menus, no forms.",
  },
  {
    step: 2,
    icon: Eye,
    title: "Perceive",
    description: "Camera and microphone stream is read for signage, numbers, and structured signals.",
  },
  {
    step: 3,
    icon: Map,
    title: "Plan",
    description: "The plan is grounded against live external data or your own stored profile — never perception alone.",
  },
  {
    step: 4,
    icon: Navigation,
    title: "Act",
    description: "Concise guidance is spoken — or, for Personal Admin, a call is placed or a form is filled.",
  },
  {
    step: 5,
    icon: RefreshCw,
    title: "Verify / Replan",
    description: "Every new signal is checked against the plan. A contradiction triggers an automatic replan.",
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" aria-labelledby="how-it-works-heading" className="border-t border-border">
      <Reveal className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 id="how-it-works-heading" className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            One loop. Every task.
          </h2>
          <p className="mt-4 text-pretty text-lg text-muted-foreground">
            The same five-stage loop runs behind every task Argus takes on — this loop, not any single feature, is
            the actual product.
          </p>
        </div>

        <div className="mt-14 flex flex-col gap-4 lg:flex-row lg:items-stretch">
          {STEPS.map((step) => (
            <LoopStep key={step.step} {...step} />
          ))}
        </div>
      </Reveal>
    </section>
  );
}
