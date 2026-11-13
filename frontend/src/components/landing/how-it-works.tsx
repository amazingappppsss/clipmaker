/** Three steps (PRD §4) on a white panel that overlaps the hero, with hand-drawn arrows. */
import { Film } from "lucide-react";
import type { ReactNode } from "react";

import { Squiggle } from "@/components/landing/squiggle";

function Step({ title, body, children }: { title: string; body: string; children: ReactNode }) {
  return (
    <li className="flex flex-col items-center rounded-[1.75rem] bg-sunken px-6 pt-8 pb-7 text-center">
      <h3 className="display-heavy text-xl sm:text-2xl">{title}</h3>
      <p className="mt-2 max-w-[16rem] text-sm text-muted">{body}</p>
      <div className="mt-6 flex min-h-16 items-center justify-center">{children}</div>
    </li>
  );
}

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="relative z-10 mx-2 -mt-20 scroll-mt-8 rounded-[2rem] bg-surface px-4 py-10 sm:mx-4 sm:rounded-[2.75rem] sm:px-8 sm:py-12"
    >
      <ol className="relative grid gap-4 md:grid-cols-3 md:gap-8">
        <Step title="Drop your video" body="Podcasts, interviews, lessons — up to 4 hours.">
          <span className="inline-flex items-center gap-2 rounded-full bg-blue py-2 pr-2 pl-4 text-sm font-semibold text-white">
            <Film className="size-4" aria-hidden />
            podcast-ep42.mp4
            <span className="rounded-full bg-lime px-2.5 py-0.5 text-xs font-bold text-ink">
              1:12:40
            </span>
          </span>
        </Step>
        <Step
          title="AI finds the moments"
          body="It reads the whole conversation first — then picks."
        >
          <span className="inline-flex items-center gap-3 rounded-full border-2 border-ink bg-white py-1.5 pr-1.5 pl-5 text-sm font-semibold">
            Complete moments found
            <span className="grid size-9 place-items-center rounded-full bg-lime font-display font-black">
              5
            </span>
          </span>
        </Step>
        <Step title="Post finished shorts" body="Captions, hooks, titles & hashtags included.">
          <span className="rounded-3xl rounded-bl-none bg-lime px-6 py-3 text-left">
            <span className="block text-[11px] font-semibold tracking-wide uppercase">
              Ready to post
            </span>
            <span className="display-heavy block text-3xl">5 clips</span>
          </span>
        </Step>
        <Squiggle className="absolute top-1/2 left-[31.5%] hidden w-12 -translate-y-1/2 text-ink md:block" />
        <Squiggle
          className="absolute top-1/2 left-[64.5%] hidden w-12 -translate-y-1/2 text-ink md:block"
          variant={2}
        />
      </ol>
    </section>
  );
}
