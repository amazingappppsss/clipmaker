/**
 * Pre-launch waitlist page. One job: trade an email address for something worth more than
 * the email, and prove the product works before asking.
 *
 * The proof is the same live "watch it read" panel the landing page uses, because a claim
 * about picking good moments is worth less than watching moments get rejected.
 */
import type { Metadata } from "next";
import { Suspense } from "react";

import { AiReads } from "@/components/landing/ai-reads";
import { SiteFooter } from "@/components/landing/site-footer";
import { SpotsLeft } from "@/components/waitlist/spots-left";
import { WaitlistForm } from "@/components/waitlist/waitlist-form";
import { FOUNDING_SPOTS, OFFER, PROMISES } from "@/lib/offer";

export const metadata: Metadata = {
  title: "Clip2Easy — founding members",
  description:
    "Join the first 100. We clip your first episode by hand before launch, free, and lock your price at half off for life.",
};

export default function WaitlistPage() {
  return (
    <>
      <main>
        <section className="blue-grid relative mx-2 mt-2 overflow-hidden rounded-[2rem] px-4 pt-10 pb-16 sm:mx-4 sm:mt-4 sm:rounded-[2.75rem] sm:px-8 sm:pt-14 sm:pb-20">
          <div className="relative mx-auto max-w-3xl text-center">
            <p className="animate-pop inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-1.5 text-xs font-bold tracking-wide text-white uppercase ring-1 ring-white/30">
              <span className="size-2 animate-pulse rounded-full bg-lime" />
              Not launched yet · first {FOUNDING_SPOTS} only
            </p>

            <h1 className="display-heavy animate-pop mt-6 text-[clamp(2rem,7vw,4.25rem)] leading-[0.95] text-white">
              <span className="block">Send us one episode.</span>
              <span className="block whitespace-nowrap">
                We&rsquo;ll clip it{" "}
                <span className="rounded-2xl bg-lime px-3 text-ink">by hand.</span>
              </span>
            </h1>

            <p className="animate-pop mx-auto mt-6 max-w-2xl text-lg leading-snug font-semibold text-white [text-shadow:0_1px_2px_rgb(5_10_60/0.35)] [animation-delay:120ms] sm:text-xl">
              Clip2Easy isn&rsquo;t open to everyone yet. The first {FOUNDING_SPOTS} people get
              their first episode cut for free before launch, and half off for life after it.
            </p>

            <div className="animate-pop mx-auto mt-9 max-w-xl text-left [animation-delay:200ms]">
              <Suspense fallback={<div className="h-16" />}>
                <WaitlistForm source="waitlist-hero" />
              </Suspense>
              <p className="mt-4 text-center text-sm font-semibold text-white/90">
                No card. No account. One email when your spot opens.
              </p>
            </div>

            <SpotsLeft />
          </div>
        </section>

        {/* The offer, itemised. */}
        <section aria-labelledby="offer-heading" className="px-4 pt-20 sm:px-8">
          <div className="mx-auto max-w-6xl">
            <p className="text-center text-xs font-bold tracking-widest text-blue uppercase">
              What founding members get
            </p>
            <h2 id="offer-heading" className="display-heavy mt-3 text-center text-4xl sm:text-6xl">
              Four things,{" "}
              <span className="text-blue">none of them &ldquo;early access&rdquo;</span>
            </h2>

            <ol className="mt-12 grid gap-4 md:grid-cols-2">
              {OFFER.map((item, i) => (
                <li key={item.title} className="rounded-[1.75rem] bg-surface p-7 ring-1 ring-line">
                  <div className="flex items-center gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-ink font-display font-black text-lime">
                      {i + 1}
                    </span>
                    <span className="text-xs font-bold tracking-widest text-blue uppercase">
                      {item.kicker}
                    </span>
                  </div>
                  <h3 className="display-heavy mt-5 text-xl sm:text-2xl">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{item.body}</p>
                  <p className="mt-4 inline-block rounded-full bg-lime px-3 py-1 text-xs font-black text-ink uppercase">
                    {item.worth}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Proof before the ask is repeated. */}
        <AiReads />

        {/* What they're actually agreeing to. */}
        <section aria-labelledby="promise-heading" className="px-4 pt-24 sm:px-8">
          <div className="mx-auto max-w-3xl rounded-[2rem] bg-surface p-7 ring-1 ring-line sm:p-10">
            <h2 id="promise-heading" className="display-heavy text-2xl sm:text-3xl">
              What happens to your email
            </h2>
            <ul className="mt-5 space-y-3">
              {PROMISES.map((line) => (
                <li key={line} className="flex gap-3 text-sm text-muted">
                  <span className="mt-2 size-1.5 shrink-0 rounded-full bg-blue" />
                  {line}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* The ask again, now that they've seen it work. */}
        <section className="px-4 py-24 sm:px-8">
          <div className="blue-grid mx-auto max-w-3xl rounded-[2rem] px-6 py-12 text-center sm:px-10">
            <h2 className="display-heavy text-3xl text-white sm:text-5xl">
              One link. One free episode.
            </h2>
            <p className="mt-4 text-lg font-semibold text-white/90">
              Then half off for as long as you use it.
            </p>
            <div className="mx-auto mt-8 max-w-xl text-left">
              <Suspense fallback={<div className="h-16" />}>
                <WaitlistForm source="waitlist-footer" />
              </Suspense>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
