/**
 * The product landing page, as it will be once we open to everyone. Parked here while `/`
 * is the waitlist: it's the page to promote the day sign-ups are live, not before.
 */
import type { Metadata } from "next";

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

export const metadata: Metadata = {
  title: "Clip2Easy — Paste a video. Get finished shorts.",
};

export default function ProductPage() {
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
