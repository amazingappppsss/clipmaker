"use client";

/**
 * Landing hero: the promise and the product's single input, front and centre.
 * Dropping a file here hands it to /new (via sign-in when needed) — no re-picking.
 */
import { Check, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { VideoDropZone } from "@/components/upload/video-drop-zone";
import { Alert } from "@/components/ui/alert";
import { useAuth } from "@/lib/auth/auth-provider";
import { setPendingUpload } from "@/lib/pending-upload";

const PROMISES = [
  "Finds the best moments",
  "Reframes to 9:16",
  "Captions & titles",
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
    <section className="relative overflow-hidden px-4 pt-16 pb-20 sm:px-6 sm:pt-24">
      <div className="mx-auto max-w-4xl text-center">
        <p className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1.5 text-sm text-ink-soft shadow-sm">
          <Sparkles className="size-4 text-magenta" aria-hidden />
          Your autonomous short-form video editor
        </p>
        <h1 className="text-[2.75rem] leading-[1.02] font-semibold tracking-[-0.035em] sm:text-7xl">
          Paste a video.
          <br />
          Get{" "}
          <span className="font-display font-normal italic tracking-normal brand-text pr-1">
            finished shorts.
          </span>
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg text-muted">
          Upload a podcast or long video. ClipMaker watches all of it, picks the moments worth
          sharing, and edits them into ready-to-post vertical clips.
        </p>
      </div>

      <div className="relative mx-auto mt-12 max-w-2xl">
        <div
          aria-hidden
          className="brand-glow pointer-events-none absolute -inset-x-16 -inset-y-10 opacity-60"
        />
        <div className="relative rounded-[1.6rem] bg-surface/70 p-2 shadow-[var(--shadow-float)] ring-1 ring-line backdrop-blur">
          <VideoDropZone onFile={handleFile} onReject={setError} />
        </div>
        {error ? (
          <div className="relative mt-4">
            <Alert tone="error">{error}</Alert>
          </div>
        ) : null}
      </div>

      <ul className="mx-auto mt-8 flex max-w-2xl flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-ink-soft">
        {PROMISES.map((p) => (
          <li key={p} className="inline-flex items-center gap-1.5">
            <Check className="size-4 text-success" aria-hidden />
            {p}
          </li>
        ))}
      </ul>
    </section>
  );
}
