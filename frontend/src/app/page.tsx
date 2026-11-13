/** Public landing page (PRD §6-A). The site header lives inside the hero (on the gradient). */
import { Capabilities } from "@/components/landing/capabilities";
import { ClipShowcase } from "@/components/landing/clip-showcase";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Pricing } from "@/components/landing/pricing";
import { SiteFooter } from "@/components/landing/site-footer";

export default function LandingPage() {
  return (
    <>
      <main>
        <Hero />
        <ClipShowcase />
        <HowItWorks />
        <Capabilities />
        <Pricing />
      </main>
      <SiteFooter />
    </>
  );
}
