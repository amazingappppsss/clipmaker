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
import { ForClippers } from "@/components/landing/for-clippers";
import { PixelCity } from "@/components/landing/pixel-city";
import { VodHud } from "@/components/landing/vod-hud";
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
        <section className="scanlines relative mx-2 mt-2 overflow-hidden rounded-[2rem] bg-night px-4 pt-8 pb-14 sm:mx-4 sm:mt-4 sm:rounded-[2.75rem] sm:px-8 sm:pt-10 sm:pb-20">
          {/* Pixel sunset behind everything, pinned to the bottom like a horizon. */}
          <PixelCity className="crisp pointer-events-none absolute inset-x-0 bottom-0 h-[62%] w-full" />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-night via-night/80 to-night/20" />

          <div className="relative mx-auto mb-6 flex max-w-6xl items-center justify-between">
            <Logo tone="light" />
            <span className="pixel text-[0.5rem] text-white/70 sm:text-[0.6rem]">
              Launching soon
            </span>
          </div>

          <div className="relative mx-auto max-w-6xl">
            <div className="flex flex-wrap items-center justify-center gap-3">
              <VodHud className="animate-pop" />
              <span className="pixel-panel animate-pop px-4 py-3">
                <span className="pixel text-[0.5rem] text-white sm:text-[0.6rem]">
                  First {FOUNDING_SPOTS} only
                </span>
              </span>
            </div>

            {/* The poster: type big enough to crop, with the clip cards sitting on top of it. */}
            <div className="relative mt-8">
              <h1 className="display-heavy animate-pop text-center text-[clamp(2.1rem,6.4vw,5.2rem)] leading-[0.86] text-white">
                <span className="block">
                  Your VOD has
                </span>
                <span className="block">
                  <span className="text-lime">30 clips</span> in it.
                </span>
                <span className="block text-white/55">You posted 2.</span>
              </h1>

              {/* Cards break the type line, the way a poster would. Hidden on phones, where
                  the headline needs the whole width. */}
              <div className="pointer-events-none absolute -top-2 -left-2 hidden rotate-[-7deg] lg:block">
                <div className="pixel-shadow-magenta border-2 border-white/80 bg-night/85 px-4 py-3">
                  <p className="pixel text-[0.55rem] text-magenta">Loud at 02:41:08</p>
                  <p className="mt-2 max-w-[13rem] text-sm font-semibold text-white">
                    Nobody said a word here. It is still the clip.
                  </p>
                </div>
              </div>
              <div className="pointer-events-none absolute -right-2 bottom-4 hidden rotate-[6deg] lg:block">
                <div className="pixel-shadow border-2 border-ink bg-lime px-4 py-3">
                  <p className="pixel text-[0.55rem] text-ink">Report card</p>
                  <p className="mt-2 max-w-[11rem] text-sm font-black text-ink">
                    8/8 checks passed
                  </p>
                </div>
              </div>
            </div>

            <div className="relative mt-10 grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_auto] lg:gap-14">
              <div className="min-w-0">
                <p className="animate-pop max-w-xl text-lg leading-snug font-semibold text-white/85 [animation-delay:120ms] sm:text-xl">
                  Clip2Easy watches the whole thing — the screaming and the gunfire, not just the
                  talking — and hands back vertical clips with the captions burned in. You pick
                  what goes out.
                </p>

                <p className="animate-pop mt-4 max-w-xl text-base leading-snug font-semibold text-teal [animation-delay:160ms]">
                  Not open yet. Send one VOD and we cut it by hand, free, before launch.
                </p>

                <div className="animate-pop mt-8 max-w-xl [animation-delay:200ms]">
                  <Suspense fallback={<div className="h-16" />}>
                    <WaitlistForm source="waitlist-hero" />
                  </Suspense>
                  <p className="mt-4 text-sm font-semibold text-white/60">
                    No card. No account. One email when your spot opens.
                  </p>
                </div>

                <SpotsLeft />
              </div>

              {/* A real short, playing itself, so something is moving the moment the page lands.
                  Made by scripts/make-demo-clip.py: the picture is licensed stock because we own
                  no footage, but the re-framing and captions are this engine's. */}
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
                <p className="pixel mt-3 text-center text-[0.5rem] text-white/50">
                  Licensed stock · real re-framing
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* The argument, then the proof: why a clipper should care, then watch it work. */}
        <ForClippers />
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
