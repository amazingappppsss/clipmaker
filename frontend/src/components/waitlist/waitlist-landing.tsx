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
import { BluePoster } from "@/components/landing/blue-poster";
import { ClipScanner } from "@/components/landing/clip-scanner";
import { Squiggle } from "@/components/landing/squiggle";
import { PixelSprite } from "@/components/landing/pixel-sprite";
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
      <main className="bg-surface">
        <section className="px-4 pt-6 pb-4 sm:px-8">
          <div className="mx-auto flex max-w-6xl items-center justify-between">
            <Logo />
            <span className="rounded-full bg-sunken px-3 py-1.5 text-xs font-semibold text-muted">
              not open yet · first {FOUNDING_SPOTS} only
            </span>
          </div>
        </section>

        <section className="px-4 pt-10 pb-6 text-center sm:px-8 sm:pt-16">
          <div className="mx-auto max-w-4xl">
            {/* Lowercase, light, tight: the headline is a sentence, not a shout. The sprites
                are the only ornament on the page, so they carry the personality. */}
            <h1 className="headline text-[clamp(2.2rem,6vw,4.4rem)] text-ink">
              your <PixelSprite name="controller" className="size-[0.85em]" /> stream has 30
              clips in it.{" "}
              <span className="whitespace-nowrap">you posted 2.</span>
            </h1>

            <p className="mx-auto mt-7 max-w-2xl text-lg leading-relaxed text-ink-soft">
              Clip2Easy listens to the whole stream — the screaming and the gunfire, not just
              the talking — and hands back vertical clips{" "}
              <PixelSprite name="phone" className="size-[1.25em]" /> with the captions burned in.
            </p>

            <p className="mx-auto mt-3 flex max-w-2xl flex-wrap items-center justify-center gap-x-2 gap-y-2 text-base text-muted">
              works on
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-sunken px-2.5 py-1 font-semibold text-ink">
                twitch streams
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-sunken px-2.5 py-1 font-semibold text-ink">
                youtube links
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-sunken px-2.5 py-1 font-semibold text-ink">
                your own files
              </span>
            </p>

            <div className="relative mx-auto mt-9 max-w-xl">
              {/* One hand-drawn arrow and one sticker: enough energy to stop the page reading
                  as a template, not so much that the calm is gone. */}
              <Squiggle
                className="pointer-events-none absolute -top-10 -left-16 hidden size-20 -scale-x-100 text-lime sm:block"
                variant={2}
                aria-hidden
              />
              <span className="absolute -top-7 -right-6 z-10 hidden rotate-[8deg] rounded-full border-2 border-ink bg-lime px-3 py-1.5 text-xs font-black text-ink uppercase shadow-[4px_4px_0_0_var(--color-ink)] sm:block">
                first one free
              </span>
              <Suspense fallback={<div className="h-16" />}>
                <WaitlistForm source="waitlist-hero" />
              </Suspense>
              <p className="mt-3 text-sm text-muted">
                No card, no account. We cut your first stream by hand, free, before launch.
              </p>
            </div>

            <SpotsLeft />
          </div>
        </section>

        {/* The claim, happening. Replaces the stock video: that could have been any page. */}
        <section className="px-4 pt-8 sm:px-8">
          <div className="mx-auto max-w-4xl">
            <ClipScanner />
          </div>
        </section>

        <BluePoster />

        {/* Proof first: watch it reject lines, then poke at a real example yourself. */}
        <AiReads />
        <LiveDemo />

        {/* The offer, itemised. */}
        <section aria-labelledby="offer-heading" className="px-4 pt-20 sm:px-8">
          <div className="mx-auto max-w-6xl">
            <p className="text-center text-xs font-bold tracking-widest text-blue uppercase">
              What founding members get
            </p>
            <h2 id="offer-heading" className="headline mt-3 text-center text-[clamp(1.9rem,4.4vw,3.2rem)]">
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
                  <h3 className="text-xl font-semibold tracking-[-0.015em]">{item.title}</h3>
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
