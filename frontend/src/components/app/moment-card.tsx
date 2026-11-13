"use client";

/**
 * One AI-picked moment: plays exactly that range of the source video (media fragment +
 * a guard that pauses at the end), with title, hook, transcript and copy-ready post text.
 * Rendered vertical clips replace the source preview once editing ships (Milestone 3).
 */
import { Check, Copy } from "lucide-react";
import { useRef, useState } from "react";

import { formatDuration } from "@/lib/format";
import type { Clip } from "@/services/api-types";

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() =>
        void navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1500);
        })
      }
      className="inline-flex items-center gap-1.5 rounded-full border-2 border-ink px-3 py-1 text-xs font-bold hover:bg-ink hover:text-white"
    >
      {copied ? (
        <Check className="size-3.5" aria-hidden />
      ) : (
        <Copy className="size-3.5" aria-hidden />
      )}
      {copied ? "Copied" : label}
    </button>
  );
}

export function MomentCard({ clip, sourceUrl }: { clip: Clip; sourceUrl: string | null }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const start = clip.start_seconds ?? 0;
  const end = clip.end_seconds ?? start;
  const post = [clip.social_caption, clip.hashtags.join(" ")].filter(Boolean).join("\n\n");

  return (
    <article className="overflow-hidden rounded-[1.75rem] bg-surface ring-1 ring-line">
      <div className="relative bg-ink">
        {sourceUrl ? (
          <video
            ref={videoRef}
            src={`${sourceUrl}#t=${start.toFixed(2)},${end.toFixed(2)}`}
            controls
            preload="metadata"
            className="aspect-video w-full"
            onTimeUpdate={(e) => {
              if (e.currentTarget.currentTime >= end) e.currentTarget.pause();
            }}
          />
        ) : (
          <div className="aspect-video" />
        )}
        <span className="absolute top-3 left-3 rounded-full bg-lime px-3 py-1 font-display text-xs font-black text-ink">
          #{clip.rank}
        </span>
        <span className="absolute top-3 right-3 rounded-full bg-black/70 px-2.5 py-1 text-xs font-semibold text-white tabular-nums">
          {formatDuration(start)}–{formatDuration(end)} · {formatDuration(clip.duration_seconds)}
        </span>
      </div>
      <div className="space-y-4 p-6">
        <div>
          <h3 className="display-heavy text-xl">{clip.title}</h3>
          {clip.hook ? <p className="mt-2 font-semibold text-blue">{clip.hook}</p> : null}
        </div>
        {clip.transcript ? (
          <details className="group rounded-2xl bg-sunken p-4 text-sm">
            <summary className="cursor-pointer font-semibold">What&apos;s said</summary>
            <p className="mt-2 leading-relaxed text-ink-soft">{clip.transcript}</p>
          </details>
        ) : null}
        {clip.social_caption ? (
          <p className="text-sm text-ink-soft">{clip.social_caption}</p>
        ) : null}
        {clip.hashtags.length ? (
          <ul className="flex flex-wrap gap-1.5">
            {clip.hashtags.map((tag) => (
              <li
                key={tag}
                className="rounded-full bg-blue-soft px-2.5 py-1 text-xs font-semibold text-blue"
              >
                {tag}
              </li>
            ))}
          </ul>
        ) : null}
        {clip.alt_titles.length ? (
          <p className="text-xs text-muted">
            <span className="font-semibold text-ink-soft">Other titles:</span>{" "}
            {clip.alt_titles.join(" · ")}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2 pt-1">
          {post ? <CopyButton text={post} label="Copy post text" /> : null}
          {clip.title ? <CopyButton text={clip.title} label="Copy title" /> : null}
        </div>
      </div>
    </article>
  );
}
