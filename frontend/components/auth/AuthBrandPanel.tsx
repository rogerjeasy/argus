import { Logo } from "@/components/marketing/Logo";
import { WatchingRings } from "@/components/marketing/WatchingRings";

export function AuthBrandPanel() {
  return (
    <div className="relative hidden overflow-hidden bg-gradient-to-br from-primary to-primary-deep px-12 py-16 text-primary-foreground lg:flex lg:w-1/2 lg:flex-col lg:justify-between">
      <WatchingRings
        rich
        className="pointer-events-none absolute -right-24 top-1/2 h-[520px] w-[520px] -translate-y-1/2 text-primary-foreground/25"
      />
      <div className="relative">
        <Logo className="text-primary-foreground" />
      </div>
      <p className="relative max-w-sm text-pretty text-lg font-medium leading-relaxed">
        Argus perceives, plans, and acts in real time — a seeing-eye copilot for the moments that matter most.
      </p>
    </div>
  );
}
