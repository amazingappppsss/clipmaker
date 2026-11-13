/** Public landing page (PRD §6-A). */
import { Capabilities } from "@/components/landing/capabilities";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Pricing } from "@/components/landing/pricing";
import { ReframeVisual } from "@/components/landing/reframe-visual";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteHeader } from "@/components/landing/site-header";

export default function LandingPage() {
  return (
    <>
      <SiteHeader />
      <main>
        <Hero />
        <ReframeVisual />
        <HowItWorks />
        <Capabilities />
        <Pricing />
      </main>
      <SiteFooter />
    </>
  );
}
