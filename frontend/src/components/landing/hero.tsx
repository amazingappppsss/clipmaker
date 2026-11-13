"use client";

/**
 * Landing hero: full-bleed animated gradient, huge headline, and the product's single input.
 * Dropping a file here hands it to /new (via sign-in when needed) — no re-picking.
 */
import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { SiteHeader } from "@/components/landing/site-header";
import { VideoDropZone } from "@/components/upload/video-drop-zone";
import { Alert } from "@/components/ui/alert";
import { useAuth } from "@/lib/auth/auth-provider";
import { setPendingUpload } from "@/lib/pending-upload";

const PROMISES = [
  "Best moments, auto-picked",
  "9:16 speaker framing",
  "Animated captions",
  "Quality-checked",
];

export function Hero() {
  const router = useRouter();
  const { status } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const handleFile = (file: File): void => {
    setPendingUpload(file);
    router.push(status === "signed_in" ? "/new" : "/login?next=/new");
  };

  return (
    <section className="mesh-gradient rounded-b-[2.5rem] pb-40 sm:rounded-b-[4rem] sm:pb-48">
      <SiteHeader />
      <div className="mx-auto max-w-5xl px-4 pt-12 text-center sm:px-6 sm:pt-20">
        <p className="animate-pop mx-auto inline-flex items-center gap-2 rounded-full bg-white/20 px-4 py-2 text-sm font-semibold text-white ring-1 ring-white/30 backdrop-blur">
          <Sparkles className="size-4" aria-hidden />
          The AI editor that makes your shorts for you
        </p>
        <h1 className="animate-pop mt-7 text-[3.25rem] leading-[0.95] font-extrabold tracking-[-0.04em] text-white [animation-delay:80ms] sm:text-8xl">
          Paste a video.
          <br />
          Get{" "}
          <span className="relative inline-block">
            <span
              aria-hidden
              className="absolute inset-x-[-0.12em] bottom-[0.06em] h-[0.42em] -rotate-1 rounded-lg bg-sun"
            />
            <span className="relative text-ink">finished shorts.</span>
          </span>
        </h1>
        <p className="animate-pop mx-auto mt-7 max-w-2xl text-lg font-medium text-white/90 [animation-delay:160ms] sm:text-xl">
          Upload a podcast or long video. ClipMaker watches all of it, picks the moments worth
          sharing, and edits them into ready-to-post vertical clips.
        </p>

        <div className="animate-pop mx-auto mt-10 max-w-2xl [animation-delay:240ms]">
          <VideoDropZone variant="bar" onFile={handleFile} onReject={setError} />
          {error ? (
            <div className="mt-4 text-left">
              <Alert tone="error">{error}</Alert>
            </div>
          ) : null}
        </div>

        <ul className="mx-auto mt-7 flex max-w-3xl flex-wrap justify-center gap-2 text-sm font-semibold text-white">
          {PROMISES.map((p) => (
            <li
              key={p}
              className="rounded-full bg-white/15 px-3.5 py-1.5 ring-1 ring-white/25 backdrop-blur"
            >
              {p}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
