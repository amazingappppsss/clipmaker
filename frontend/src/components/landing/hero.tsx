"use client";

/**
 * Landing hero: cobalt grid panel, giant uppercase headline, floating glass clip cards,
 * squiggles, a spinning CTA badge and the product's single input.
 * Dropping a file here hands it to /new (via sign-in when needed) — no re-picking.
 */
import { useRouter } from "next/navigation";
import { useState } from "react";

import { SiteHeader } from "@/components/landing/site-header";
import { SpinBadge } from "@/components/landing/spin-badge";
import { Squiggle } from "@/components/landing/squiggle";
import { VideoDropZone } from "@/components/upload/video-drop-zone";
import { Alert } from "@/components/ui/alert";
import { useAuth } from "@/lib/auth/auth-provider";
import { setPendingUpload } from "@/lib/pending-upload";

/** Small frosted card showing a vertical clip (illustration). */
function GlassClip({
  tone,
  word,
  label,
  meta,
  className,
  tilt,
}: {
  tone: string;
  word: string;
  label: string;
  meta: string;
  className: string;
  tilt: string;
}) {
  return (
    <div
      aria-hidden
      className={`glass animate-float absolute hidden w-32 rounded-[1.6rem] p-2.5 lg:block xl:w-36 ${className}`}
      style={{ ["--tilt" as string]: tilt }}
    >
      <div className={`relative aspect-[9/14] overflow-hidden rounded-[1.1rem] ${tone}`}>
        <span className="absolute bottom-0 left-1/2 h-[42%] w-[70%] -translate-x-1/2 rounded-t-full bg-white/15" />
        <span className="absolute bottom-[40%] left-1/2 size-10 -translate-x-1/2 rounded-full bg-white/20" />
        <span className="absolute inset-x-1 bottom-[22%] text-center font-display text-sm font-black text-lime uppercase [text-shadow:0_2px_6px_rgb(0_0_0/0.5)]">
          {word}
        </span>
      </div>
      <p className="mt-2 truncate text-center text-[13px] font-bold text-white">{label}</p>
      <p className="text-center text-[11px] text-white/75">{meta}</p>
    </div>
  );
}

export function Hero() {
  const router = useRouter();
  const { status } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const handleFile = (file: File): void => {
    setPendingUpload(file);
    router.push(status === "signed_in" ? "/new" : "/login?next=/new");
  };

  return (
    <section className="blue-grid relative mx-2 mt-2 overflow-hidden rounded-[2rem] pb-32 sm:mx-4 sm:mt-4 sm:rounded-[2.75rem] sm:pb-40">
      <SiteHeader />

      <div className="relative mx-auto max-w-6xl px-4 pt-10 text-center sm:px-8 sm:pt-14">
        <h1 className="display-heavy animate-pop text-[clamp(2.3rem,8vw,6rem)] text-white">
          <span className="block whitespace-nowrap">
            <span className="text-lime">#</span>Long video
          </span>
          <span className="block whitespace-nowrap">to shorts</span>
          <span className="block whitespace-nowrap">in one click</span>
        </h1>

        <GlassClip
          tone="video-tone-1"
          word="changed"
          label="Clip 01 · 0:41"
          meta="The habit that…"
          className="top-0 right-[0%] xl:right-[2%]"
          tilt="8deg"
        />
        <GlassClip
          tone="video-tone-2"
          word="focus."
          label="Clip 02 · 0:58"
          meta="Why startups die…"
          className="top-[40%] left-[0%] [animation-delay:-3s] xl:left-[2%]"
          tilt="-7deg"
        />
        <Squiggle className="absolute -top-6 left-[8%] hidden w-24 -rotate-12 text-lime md:block lg:left-[12%]" />
        <Squiggle
          className="absolute top-[44%] right-[13%] hidden w-20 rotate-[160deg] text-lime xl:block"
          variant={2}
        />
        <SpinBadge className="absolute right-[2%] bottom-[-3.5rem] hidden sm:grid lg:right-[6%]" />

        <p className="animate-pop mx-auto mt-10 max-w-xl text-base font-medium text-white/90 [animation-delay:120ms] sm:text-lg">
          Upload a podcast or long video. ClipMaker finds the best moments and edits them into
          ready-to-post vertical clips — captions, hooks and framing included.
        </p>
        <div className="animate-pop mx-auto mt-8 max-w-xl text-left [animation-delay:200ms]">
          <VideoDropZone variant="bar" onFile={handleFile} onReject={setError} />
          {error ? (
            <div className="mt-4">
              <Alert tone="error">{error}</Alert>
            </div>
          ) : null}
          <p className="mt-5 text-center text-xs font-medium text-white/75">
            15 free minutes · No credit card · Only upload videos you have the rights to
          </p>
        </div>
      </div>
    </section>
  );
}
