/** Public landing page (PRD §6-A). The site header lives inside the hero panel. */
import { AiReads } from "@/components/landing/ai-reads";
import { Capabilities } from "@/components/landing/capabilities";
import { Faq } from "@/components/landing/faq";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { LiveDemo } from "@/components/landing/live-demo";
import { Pricing } from "@/components/landing/pricing";
import { SiteFooter } from "@/components/landing/site-footer";
import { StickyCta } from "@/components/landing/sticky-cta";
import { WhyBetter } from "@/components/landing/why-better";

export default function LandingPage() {
  return (
    <>
      <main>
        <Hero />
        <HowItWorks />
        <AiReads />
        <LiveDemo />
        <WhyBetter />
        <Capabilities />
        <Pricing />
        <Faq />
      </main>
      <SiteFooter />
      <StickyCta />
    </>
  );
}
