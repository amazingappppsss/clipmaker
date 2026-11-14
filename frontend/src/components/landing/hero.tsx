"use client";

/**
 * Landing hero: cobalt grid panel, giant uppercase headline, two phones showing the real
 * output style (animated captions, hook title, score), squiggles, a spinning CTA badge and
 * the product's single input.
 * Dropping a file here hands it to /new (via sign-in when needed) — no re-picking.
 */
import { useState } from "react";

import { PhoneClip } from "@/components/landing/phone-clip";
import { SiteHeader } from "@/components/landing/site-header";
import { SpinBadge } from "@/components/landing/spin-badge";
import { Squiggle } from "@/components/landing/squiggle";
import { LinkBar } from "@/components/upload/link-bar";
import { Alert } from "@/components/ui/alert";

export function Hero() {
  const [error, setError] = useState<string | null>(null);

  return (
    <section className="blue-grid relative mx-2 mt-2 overflow-hidden rounded-[2rem] pb-32 sm:mx-4 sm:mt-4 sm:rounded-[2.75rem] sm:pb-40">
      <SiteHeader />

      <div className="relative mx-auto max-w-6xl px-4 pt-8 text-center sm:px-8 sm:pt-12">
        <p className="animate-pop mx-auto inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-1.5 text-xs font-bold tracking-wide text-white ring-1 ring-white/30 uppercase">
          <span className="size-2 animate-pulse rounded-full bg-lime" />
          AI clip editor for podcasts &amp; interviews
        </p>
        <h1 className="display-heavy animate-pop mt-6 text-[clamp(1.55rem,7.2vw,4.4rem)] text-white">
          <span className="block whitespace-nowrap">One episode.</span>
          <span className="block whitespace-nowrap">
            <span className="text-lime">10</span> viral shorts.
          </span>
          <span className="block whitespace-nowrap">
            Zero <span className="rounded-2xl bg-lime px-3 text-ink">editing.</span>
          </span>
        </h1>

        <PhoneClip
          className="animate-float absolute top-4 -right-10 hidden xl:block 2xl:-right-20"
          tone="video-tone-1"
          title="Rogan was stunned"
          caption={["He", "spends", "$28", "on", "lunch", "every", "single", "day"]}
          highlight={["$28"]}
          score={92}
          hook="Shocking number"
        />
        <PhoneClip
          className="animate-float absolute top-[40%] -left-10 hidden [animation-delay:-3s] xl:block 2xl:-left-20"
          tone="video-tone-2"
          title="The worst advice I ever got"
          caption={["I", "thought", "it", "was", "easy", "money.", "I", "was", "wrong."]}
          score={88}
          hook="Confession"
        />
        <Squiggle className="absolute -top-6 left-[8%] hidden w-24 -rotate-12 text-lime md:block lg:left-[12%]" />
        <Squiggle
          className="absolute top-[44%] right-[13%] hidden w-20 rotate-[160deg] text-lime xl:block"
          variant={2}
        />
        <SpinBadge className="absolute right-[2%] bottom-[-3.5rem] hidden sm:grid lg:right-[6%]" />

        <p className="animate-pop mx-auto mt-10 max-w-xl text-base font-medium text-white/90 [animation-delay:120ms] sm:text-lg">
          Paste a YouTube link. Clip2Easy finds the moments people actually stop scrolling for, then
          cuts, captions and frames them into vertical shorts you can post today.
        </p>
        <div className="animate-pop mx-auto mt-8 max-w-xl text-left [animation-delay:200ms]">
          <LinkBar onError={setError} />
          {error ? (
            <div className="mt-4">
              <Alert tone="error">{error}</Alert>
            </div>
          ) : null}
          <p className="mt-5 text-center text-xs font-medium text-white/75">
            15 free minutes · No credit card · Clips in minutes · Only use videos you have the
            rights to
          </p>
        </div>
      </div>
    </section>
  );
}
