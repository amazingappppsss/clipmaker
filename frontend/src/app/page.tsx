/** Public landing page (PRD §6-A). The site header lives inside the hero panel. */
import { Capabilities } from "@/components/landing/capabilities";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Pricing } from "@/components/landing/pricing";
import { ProductPreview } from "@/components/landing/product-preview";
import { SiteFooter } from "@/components/landing/site-footer";

export default function LandingPage() {
  return (
    <>
      <main>
        <Hero />
        <HowItWorks />
        <section aria-labelledby="preview-heading" className="px-4 pt-24 sm:px-8">
          <div className="mx-auto max-w-6xl">
            <h2
              id="preview-heading"
              className="display-heavy mb-12 text-center text-4xl sm:text-6xl"
            >
              See what you <span className="text-blue">get</span>
            </h2>
            <ProductPreview />
          </div>
        </section>
        <Capabilities />
        <Pricing />
      </main>
      <SiteFooter />
    </>
  );
}
