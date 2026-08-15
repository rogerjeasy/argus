import type { Metadata } from "next";
import { HomeAuthGuard } from "@/components/marketing/HomeAuthGuard";
import { MarketingNav } from "@/components/marketing/MarketingNav";
import { HeroSection } from "@/components/marketing/HeroSection";
import { ProblemSection } from "@/components/marketing/ProblemSection";
import { HowItWorksSection } from "@/components/marketing/HowItWorksSection";
import { FlagshipDomainsSection } from "@/components/marketing/FlagshipDomainsSection";
import { MultimodalSection } from "@/components/marketing/MultimodalSection";
import { ArchitectureSection } from "@/components/marketing/ArchitectureSection";
import { TrustSection } from "@/components/marketing/TrustSection";
import { FinalCta } from "@/components/marketing/FinalCta";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";

export const metadata: Metadata = {
  title: "Argus — The Agentic Seeing-Eye Copilot",
  description:
    "Argus perceives, plans, acts, and replans in real time to complete real-world tasks for blind and low-vision people — from live transit navigation to a real outbound phone call.",
};

export default function HomePage() {
  return (
    <HomeAuthGuard>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <MarketingNav />
      <main id="main-content">
        <HeroSection />
        <ProblemSection />
        <HowItWorksSection />
        <FlagshipDomainsSection />
        <MultimodalSection />
        <ArchitectureSection />
        <TrustSection />
        <FinalCta />
      </main>
      <MarketingFooter />
    </HomeAuthGuard>
  );
}
