"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Menu } from "lucide-react";
import { motion, useReducedMotion, useScroll } from "framer-motion";
import { useAuth } from "@/lib/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { ThemeToggle } from "@/components/ThemeToggle";
import { cn } from "@/lib/utils";
import { Logo } from "./Logo";

const NAV_LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#domains", label: "Domains" },
  { href: "#multimodal", label: "Multimodal" },
  { href: "#architecture", label: "Architecture" },
  { href: "#trust", label: "Trust" },
] as const;

export function MarketingNav() {
  const { user } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const prefersReducedMotion = useReducedMotion();
  const { scrollYProgress } = useScroll();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const ctaLabel = user ? "Open Argus" : "Sign in";

  const desktopCta = (
    <Button asChild>
      <Link href={user ? "/dashboard" : "/sign-in"}>{ctaLabel}</Link>
    </Button>
  );

  const mobileCta = (
    <Button asChild size="lg" className="w-full">
      <Link href={user ? "/dashboard" : "/sign-in"}>{ctaLabel}</Link>
    </Button>
  );

  return (
    <header
      className={cn(
        "sticky top-0 z-40 w-full border-b transition-colors duration-200 relative",
        scrolled ? "border-border bg-background/85 backdrop-blur-sm" : "border-transparent bg-transparent"
      )}
    >
      <nav
        aria-label="Primary"
        className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8"
      >
        <Logo />

        <ul className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="inline-flex min-h-11 -mx-2 items-center px-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="hidden items-center gap-3 md:flex">
          <ThemeToggle />
          {desktopCta}
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon" aria-label="Open menu">
                <Menu className="h-5 w-5" aria-hidden="true" />
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetTitle>Menu</SheetTitle>
              <ul className="flex flex-col gap-1">
                {NAV_LINKS.map((link) => (
                  <li key={link.href}>
                    <SheetClose asChild>
                      <a
                        href={link.href}
                        className="block rounded-lg px-3 py-3 text-base font-medium text-foreground hover:bg-secondary"
                      >
                        {link.label}
                      </a>
                    </SheetClose>
                  </li>
                ))}
              </ul>
              <SheetClose asChild>{mobileCta}</SheetClose>
            </SheetContent>
          </Sheet>
        </div>
      </nav>
      {!prefersReducedMotion && (
        <motion.div
          aria-hidden="true"
          className="absolute inset-x-0 bottom-0 h-0.5 origin-left bg-primary"
          style={{ scaleX: scrollYProgress }}
        />
      )}
    </header>
  );
}
