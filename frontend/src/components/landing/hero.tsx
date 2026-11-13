"use client";

/**
 * Landing hero: headline, the product's single input, and the product preview right below.
 * Dropping a file here hands it to /new (via sign-in when needed) — no re-picking.
 */
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ProductPreview } from "@/components/landing/product-preview";
import { SiteHeader } from "@/components/landing/site-header";
import { VideoDropZone } from "@/components/upload/video-drop-zone";
import { Alert } from "@/components/ui/alert";
import { useAuth } from "@/lib/auth/auth-provider";
import { setPendingUpload } from "@/lib/pending-upload";

export function Hero() {
  const router = useRouter();
  const { status } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const handleFile = (file: File): void => {
    setPendingUpload(file);
    router.push(status === "signed_in" ? "/new" : "/login?next=/new");
  };

  return (
    <section className="spotlight overflow-hidden">
      <div aria-hidden className="grid-backdrop pointer-events-none absolute inset-0 -z-10" />
      <SiteHeader />
      <div className="mx-auto max-w-4xl px-4 pt-16 text-center sm:px-6 sm:pt-24">
        <p className="animate-pop mx-auto inline-flex items-center gap-2 rounded-full border border-line-strong bg-surface/70 px-3.5 py-1.5 text-xs font-medium text-ink-soft backdrop-blur sm:text-sm">
          <span className="size-1.5 rounded-full bg-violet-bright shadow-[0_0_8px_var(--color-violet-bright)]" />
          AI clipping for podcasts & long videos
        </p>
        <h1 className="animate-pop mt-6 text-5xl leading-[1.02] font-bold tracking-[-0.035em] [animation-delay:80ms] sm:text-7xl">
          1 long video.
          <br />
          <span className="gradient-text">10 ready-to-post shorts.</span>
        </h1>
        <p className="animate-pop mx-auto mt-6 max-w-xl text-base text-muted [animation-delay:160ms] sm:text-lg">
          ClipMaker watches your whole video, finds the moments worth sharing, and edits them into
          vertical clips with captions, hooks and speaker framing. No editing skills needed.
        </p>
        <div className="animate-pop mx-auto mt-9 max-w-2xl [animation-delay:240ms]">
          <VideoDropZone variant="bar" onFile={handleFile} onReject={setError} />
          {error ? (
            <div className="mt-3 text-left">
              <Alert tone="error">{error}</Alert>
            </div>
          ) : null}
          <p className="mt-4 text-xs text-muted">
            60 free minutes · No credit card · Only upload videos you have the rights to
          </p>
        </div>
      </div>
      <div className="animate-pop mx-auto mt-16 max-w-6xl px-4 pb-24 [animation-delay:320ms] sm:px-6">
        <ProductPreview />
      </div>
    </section>
  );
}
