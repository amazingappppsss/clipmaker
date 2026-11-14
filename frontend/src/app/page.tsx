/** Public landing page (PRD §6-A). The site header lives inside the hero panel. */
import { Capabilities } from "@/components/landing/capabilities";
import { Faq } from "@/components/landing/faq";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { LiveDemo } from "@/components/landing/live-demo";
import { Pricing } from "@/components/landing/pricing";
import { SiteFooter } from "@/components/landing/site-footer";
import { WhyBetter } from "@/components/landing/why-better";

export default function LandingPage() {
  return (
    <>
      <main>
        <Hero />
        <HowItWorks />
        <LiveDemo />
        <WhyBetter />
        <Capabilities />
        <Pricing />
        <Faq />
      </main>
      <SiteFooter />
    </>
  );
}
