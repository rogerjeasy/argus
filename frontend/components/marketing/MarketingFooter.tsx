import { Logo } from "./Logo";

const FOOTER_LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#domains", label: "Domains" },
  { href: "#multimodal", label: "Multimodal" },
  { href: "#architecture", label: "Architecture" },
  { href: "#trust", label: "Trust" },
] as const;

export function MarketingFooter() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-6 px-4 py-12 sm:px-6 lg:flex-row lg:justify-between lg:px-8">
        <div className="flex flex-col items-center gap-2 lg:items-start">
          <Logo />
          <p className="text-sm text-muted-foreground">The agentic seeing-eye copilot.</p>
        </div>

        <ul className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          {FOOTER_LINKS.map((link) => (
            <li key={link.href}>
              <a href={link.href} className="text-sm text-muted-foreground transition-colors hover:text-foreground">
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <p className="text-sm text-muted-foreground">© {new Date().getFullYear()} Argus.</p>
      </div>
    </footer>
  );
}
