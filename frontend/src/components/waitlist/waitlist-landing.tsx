"use client";

/**
 * The pre-launch page body. Rendered at `/` (we are not open yet, so the front door is the
 * waitlist, not a paste bar for a product nobody can use) and at `/waitlist`, so referral
 * links that already point there keep working.
 *
 * The order is deliberate: the ask, then proof it works, then the offer, then the ask again.
 * Nobody gives an address to a promise they haven't seen run.
 */
import { Suspense } from "react";

import { AiReads } from "@/components/landing/ai-reads";
import { PhoneClip } from "@/components/landing/phone-clip";
import { Capabilities } from "@/components/landing/capabilities";
import { LiveDemo } from "@/components/landing/live-demo";
import { Logo } from "@/components/ui/logo";
import { WhyBetter } from "@/components/landing/why-better";
import { WaitlistFooter } from "@/components/waitlist/waitlist-footer";
import { SpotsLeft } from "@/components/waitlist/spots-left";
import { WaitlistForm } from "@/components/waitlist/waitlist-form";
import { FOUNDING_SPOTS, OFFER, PROMISES } from "@/lib/offer";

export function WaitlistLanding() {
  return (
    <>
      <main>
        <section className="blue-grid relative mx-2 mt-2 overflow-hidden rounded-[2rem] px-4 pt-10 pb-16 sm:mx-4 sm:mt-4 sm:rounded-[2.75rem] sm:px-8 sm:pt-14 sm:pb-20">
          <div className="relative mx-auto mb-4 flex max-w-6xl items-center justify-between">
            <Logo tone="light" />
            <span className="text-xs font-semibold text-white/80">Launching soon</span>
          </div>

          <div className="relative mx-auto grid max-w-6xl items-center gap-10 text-center lg:grid-cols-[minmax(0,1fr)_auto] lg:gap-14 lg:text-left">
            <div className="min-w-0">
              <p className="animate-pop inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-1.5 text-xs font-bold tracking-wide text-white uppercase ring-1 ring-white/30">
                <span className="size-2 animate-pulse rounded-full bg-lime" />
                Not launched yet · first {FOUNDING_SPOTS} only
              </p>

              <h1 className="display-heavy animate-pop mt-6 text-[clamp(2rem,5vw,3.6rem)] leading-[0.95] text-white">
                <span className="block">Send us one episode.</span>
                <span className="block">
                  We&rsquo;ll clip it{" "}
                  <span className="rounded-2xl bg-lime px-3 text-ink">by hand.</span>
                </span>
              </h1>

              <p className="animate-pop mx-auto mt-6 max-w-2xl text-lg leading-snug font-semibold text-white [text-shadow:0_1px_2px_rgb(5_10_60/0.35)] [animation-delay:120ms] sm:text-xl">
                Clip2Easy isn&rsquo;t open to everyone yet. The first {FOUNDING_SPOTS} people get
                their first episode cut for free before launch, and half off for life after it.
              </p>

              <div className="animate-pop mx-auto mt-9 max-w-xl text-left [animation-delay:200ms] lg:mx-0">
                <Suspense fallback={<div className="h-16" />}>
                  <WaitlistForm source="waitlist-hero" />
                </Suspense>
                <p className="mt-4 text-center text-sm font-semibold text-white/90 lg:text-left">
                  No card. No account. One email when your spot opens.
                </p>
              </div>

              <SpotsLeft />
            </div>

            {/* A real short, playing itself, so something is moving the moment the page lands.
                Made by scripts/make-demo-clip.py: the picture is synthetic because we own no
                footage, but the captions are burned in by the same engine that captions real
                clips. Labelled below so nobody reads it as a customer's episode. */}
            <div className="mx-auto">
              <PhoneClip
                className="animate-float"
                size="lg"
                src="/demo/podcast-reframe.mp4"
                tone="video-tone-1"
                title="Auto-cropped to 9:16"
                caption={["Follows", "whoever", "is", "talking"]}
                score={94}
                hook="Speaker-tracked"
              />
              <p className="mt-2 text-center text-xs font-medium text-white/70">
                Licensed stock footage · real re-framing, demo captions
              </p>
            </div>
          </div>
        </section>

        {/* Proof first: watch it reject lines, then poke at a real example yourself. */}
        <AiReads />
        <LiveDemo />

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

        {/* Why these picks beat "the loudest sentence", and what the engine actually does. */}
        <WhyBetter />
        <Capabilities />

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
      </main>
      <WaitlistFooter />
    </>
  );
}
