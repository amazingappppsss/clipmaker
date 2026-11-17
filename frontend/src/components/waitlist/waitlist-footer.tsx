"use client";

/**
 * Footer for the pre-launch page.
 *
 * The product footer ends on "paste the link and see them in minutes", which is the wrong
 * promise here: there is nothing to paste into yet, and its link bar sends people to a sign-in
 * for a product that isn't open. This one closes on the waitlist instead.
 */
import { Suspense } from "react";

import { Logo } from "@/components/ui/logo";
import { WaitlistForm } from "@/components/waitlist/waitlist-form";
import { FOUNDING_SPOTS } from "@/lib/offer";

export function WaitlistFooter() {
  return (
    <footer className="px-2 pb-8 sm:px-4">
      <div className="blue-grid relative overflow-hidden rounded-[2rem] px-6 py-16 text-center text-white sm:rounded-[2.75rem] sm:py-20">
        <h2 className="headline mx-auto max-w-3xl text-[clamp(1.7rem,4vw,2.9rem)]">
          Your next 10 shorts are <span className="text-lime">already recorded</span>
        </h2>
        <p className="mx-auto mt-5 max-w-md font-semibold text-white/90">
          They&rsquo;re hiding in your last episode. Join the first {FOUNDING_SPOTS} and we&rsquo;ll
          cut them for you before launch.
        </p>
        <div className="mx-auto mt-8 max-w-xl text-left">
          <Suspense fallback={<div className="h-16" />}>
            <WaitlistForm source="waitlist-footer" />
          </Suspense>
        </div>
      </div>
      <div className="mx-auto mt-8 flex max-w-6xl flex-col items-center justify-between gap-4 px-4 text-sm text-muted sm:flex-row">
        <Logo />
        <p>© Clip2Easy. Only upload videos you have the rights to.</p>
      </div>
    </footer>
  );
}
