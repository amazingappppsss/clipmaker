"use client";

/**
 * One clip. When it's finished, the real vertical short plays here with a Download button;
 * until then (or if rendering failed) the picked range of the source video previews instead,
 * teaser first. Title, hook, why-it-works and copy-ready post text below.
 */
import { Check, Copy, Download } from "lucide-react";

import { TrimControls } from "@/components/app/trim-controls";
import { useRef, useState } from "react";

import { initialPlayback, nextPlayback, type Phase } from "@/lib/teaser";

import { formatDuration, hookLabel } from "@/lib/format";
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

export function MomentCard({
  clip,
  sourceUrl,
  projectId,
  onCorrected,
}: {
  clip: Clip;
  sourceUrl: string | null;
  projectId?: string;
  onCorrected?: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const start = clip.start_seconds ?? 0;
  const end = clip.end_seconds ?? start;
  const timing = {
    start,
    end,
    teaserStart: clip.teaser_start_seconds,
    teaserEnd: clip.teaser_end_seconds,
  };
  const first = initialPlayback(timing);
  const phase = useRef<Phase>(first.phase);
  const [rewinding, setRewinding] = useState(false);
  const post = [clip.social_caption, clip.hashtags.join(" ")].filter(Boolean).join("\n\n");

  return (
    <article className="overflow-hidden rounded-[1.75rem] bg-surface ring-1 ring-line">
      <div className="relative bg-ink">
        {clip.video_url ? (
          <video
            src={clip.video_url}
            poster={clip.thumbnail_url ?? undefined}
            controls
            playsInline
            preload="metadata"
            className="mx-auto aspect-[9/16] max-h-[34rem] w-full bg-black object-contain"
          />
        ) : sourceUrl ? (
          <video
            ref={videoRef}
            src={`${sourceUrl}#t=${first.at.toFixed(2)}`}
            controls
            preload="metadata"
            className="aspect-video w-full"
            onPlay={(e) => {
              if (phase.current === "done") {
                // Replay from the top: teaser first again.
                phase.current = first.phase;
                e.currentTarget.currentTime = first.at;
              }
            }}
            onTimeUpdate={(e) => {
              const step = nextPlayback(phase.current, e.currentTarget.currentTime, timing);
              if (!step) return;
              phase.current = step.phase;
              if (step.seekTo !== undefined) e.currentTarget.currentTime = step.seekTo;
              if (step.pause) e.currentTarget.pause();
              if (step.rewind) {
                setRewinding(true);
                window.setTimeout(() => setRewinding(false), 450);
              }
            }}
          />
        ) : (
          <div className="aspect-video" />
        )}
        {rewinding ? (
          <div
            className="pointer-events-none absolute inset-0 grid place-items-center bg-white/25 backdrop-blur-sm"
            aria-hidden
          >
            <span className="rounded-full bg-ink px-4 py-1.5 font-display text-sm font-black text-lime">
              ⏪ REWIND
            </span>
          </div>
        ) : null}
        <span className="absolute top-3 left-3 rounded-full bg-lime px-3 py-1 font-display text-xs font-black text-ink">
          #{clip.rank}
        </span>
        <span className="absolute top-3 right-3 rounded-full bg-black/70 px-2.5 py-1 text-xs font-semibold text-white tabular-nums">
          {formatDuration(start)}–{formatDuration(end)} · {formatDuration(clip.duration_seconds)}
        </span>
      </div>
      <div className="space-y-4 p-6">
        <div>
          <div className="flex items-start justify-between gap-3">
            <h3 className="display-heavy text-xl">{clip.title}</h3>
            {clip.score ? (
              <span
                className="shrink-0 rounded-full bg-ink px-2.5 py-1 font-display text-sm font-black text-lime tabular-nums"
                title="Stop · Stay · Share score"
              >
                {Math.round(clip.score)}
              </span>
            ) : null}
          </div>
          {hookLabel(clip.hook_type) ? (
            <span className="mt-2 inline-block rounded-full border-2 border-ink px-2.5 py-0.5 text-xs font-bold">
              🎣 {hookLabel(clip.hook_type)}
            </span>
          ) : null}
          {clip.hook ? <p className="mt-2 font-semibold text-blue">{clip.hook}</p> : null}
        </div>
        {clip.why || clip.strengths.length ? (
          <div className="rounded-2xl bg-blue-soft p-4">
            <p className="text-[0.7rem] font-bold tracking-widest text-blue uppercase">
              Why it works
            </p>
            {clip.why ? <p className="mt-1 text-sm text-ink">{clip.why}</p> : null}
            {clip.strengths.length ? (
              <ul className="mt-3 flex flex-wrap gap-1.5" aria-label="Strengths">
                {clip.strengths.map((s) => (
                  <li
                    key={s}
                    className="rounded-full bg-lime px-2.5 py-0.5 text-xs font-bold text-ink"
                  >
                    {s}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
        {clip.teaser_text ? (
          <div className="rounded-2xl border-2 border-dashed border-ink/15 p-4">
            <p className="text-[0.7rem] font-bold tracking-widest text-muted uppercase">
              Opens with a flash-forward
            </p>
            <p className="mt-1 text-sm font-semibold">“{clip.teaser_text}”</p>
            <p className="mt-1 text-xs text-muted">
              Plays first, then the clip rewinds to the start so viewers stay to see how it gets
              there.
            </p>
          </div>
        ) : null}
        {clip.five_second_moment ? (
          <blockquote className="border-l-4 border-lime pl-3 text-sm text-ink-soft italic">
            <span className="mb-0.5 block text-[0.7rem] font-bold tracking-widest text-muted not-italic uppercase">
              The moment it turns
            </span>
            “{clip.five_second_moment}”
          </blockquote>
        ) : null}
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
        {clip.edit_notes?.length ? (
          <div className="rounded-2xl bg-warning-soft p-3">
            <p className="text-xs font-bold tracking-wide text-warning uppercase">
              What we&rsquo;d fix
            </p>
            <ul className="mt-1 space-y-0.5">
              {clip.edit_notes.map((note) => (
                <li key={note.key} className="text-sm text-ink-soft">
                  {note.note}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {clip.status === "failed" && clip.error_message ? (
          <p className="rounded-2xl bg-danger-soft p-3 text-sm text-danger">{clip.error_message}</p>
        ) : null}
        <div className="flex flex-wrap gap-2 pt-1">
          {clip.download_url ? (
            <a
              href={clip.download_url}
              download
              className="inline-flex items-center gap-1.5 rounded-full bg-blue px-4 py-1.5 text-sm font-bold text-white hover:bg-blue-deep"
            >
              <Download className="size-4" aria-hidden /> Download MP4
            </a>
          ) : null}
          {post ? <CopyButton text={post} label="Copy post text" /> : null}
          {clip.title ? <CopyButton text={clip.title} label="Copy title" /> : null}
          {projectId && clip.start_seconds != null && clip.end_seconds != null ? (
            <TrimControls
              projectId={projectId}
              clipId={clip.id}
              start={clip.start_seconds}
              end={clip.end_seconds}
              onQueued={onCorrected}
            />
          ) : null}
        </div>
      </div>
    </article>
  );
}
