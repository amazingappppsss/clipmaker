"use client";

/**
 * Live processing panel: what's happening right now, on which video, and how far along.
 * Everything shown comes from the backend's real stage records — the bar is the four stages
 * that actually run (done / running / waiting), never a simulated percentage.
 */
import { Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import {
  LIVE_STEPS,
  currentLiveStep,
  elapsedLabel,
  etaLabel,
  stepCopy,
  type StepStatus,
} from "@/lib/project-state";
import { youtubeThumbnail } from "@/lib/youtube";
import type { Project } from "@/services/api-types";

function useNow(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}

export function ProcessingHero({
  project,
  steps,
  startedAt,
  clipsReady = 0,
  clipsTotal = 0,
  etaSeconds,
}: {
  project: Project;
  steps: StepStatus[];
  startedAt: string | null | undefined;
  clipsReady?: number;
  clipsTotal?: number;
  etaSeconds?: number | null;
}) {
  const now = useNow(1000);
  const src = project.source_video;
  const fromLink = src?.source_kind === "url";
  const preview = project.thumbnail_url ?? youtubeThumbnail(src?.source_url);
  const index = currentLiveStep(steps);
  const active = index >= 0 ? LIVE_STEPS[index] : undefined;
  const copy = stepCopy(active?.state ?? project.state, fromLink);
  const elapsed = elapsedLabel(startedAt, now);
  const eta = etaLabel(etaSeconds); // shown in whole minutes, so polling is enough

  return (
    <section
      className="blue-grid relative overflow-hidden rounded-[1.75rem] p-6 text-white sm:p-8"
      aria-live="polite"
    >
      <div className="grid items-center gap-8 md:grid-cols-[minmax(0,15rem)_1fr]">
        {/* The video being worked on, with a scanning line while the AI "looks" at it. */}
        <div className="relative mx-auto aspect-video w-full max-w-xs overflow-hidden rounded-2xl bg-ink ring-4 ring-white/20 md:max-w-none">
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element -- signed / external URLs
            <img src={preview} alt="" className="size-full object-cover opacity-80" />
          ) : (
            <div className="video-tone-2 size-full" />
          )}
          <span
            className="animate-scan absolute inset-x-0 h-0.5 bg-lime shadow-[0_0_18px_4px] shadow-lime/70"
            aria-hidden
          />
          <span className="absolute top-2 left-2 inline-flex items-center gap-1 rounded-full bg-lime px-2 py-0.5 text-[0.65rem] font-black text-ink uppercase">
            <Sparkles className="size-3" aria-hidden /> AI at work
          </span>
        </div>

        <div className="min-w-0">
          <p className="text-xs font-bold tracking-widest text-lime uppercase">
            {index >= 0 ? `Step ${index + 1} of ${LIVE_STEPS.length}` : "Starting"}
            {elapsed ? <span className="text-white/70"> · {elapsed} elapsed</span> : null}
            {eta ? <span className="text-white"> · {eta}</span> : null}
          </p>
          <h2 className="display-heavy mt-2 text-3xl leading-tight sm:text-4xl">{copy.title}</h2>
          <p className="mt-2 max-w-xl text-white/80">{copy.detail}</p>

          <ol className="mt-6 grid grid-cols-7 gap-1.5" aria-label="Progress">
            {LIVE_STEPS.map((step, i) => {
              const status = steps[i] ?? "pending";
              return (
                <li key={step.state} className="min-w-0">
                  <div className="h-2.5 overflow-hidden rounded-full bg-white/20">
                    <div
                      className={
                        status === "done"
                          ? "h-full w-full bg-lime"
                          : status === "current"
                            ? "stripes animate-stripes h-full w-full"
                            : status === "failed"
                              ? "h-full w-full bg-danger"
                              : "h-full w-0"
                      }
                    />
                  </div>
                  <p
                    className={`mt-1.5 hidden truncate text-[0.65rem] sm:block ${status === "pending" ? "text-white/60" : "font-semibold"}`}
                  >
                    {step.label}
                  </p>
                </li>
              );
            })}
          </ol>
          {clipsTotal ? (
            <p className="mt-5 inline-flex items-center gap-2 rounded-full bg-lime px-4 py-1.5 text-sm font-black text-ink">
              {clipsReady} of {clipsTotal} shorts ready
            </p>
          ) : null}
          <p className="mt-5 text-sm text-white/70">
            Usually a few minutes. You can close this tab; we&apos;ll keep going.
          </p>
        </div>
      </div>
    </section>
  );
}

/**
 * The first minute has nothing to show yet — the transcript isn't back, so there are no
 * moments to stream in. Rather than leave a dead screen, say what the AI is weighing right
 * now. These are our real criteria, from docs/CLIP_FRAMEWORK.md, not filler stats.
 */
const WHILE_YOU_WAIT: Array<[string, string]> = [
  [
    "It scores 11 signals per moment",
    "Hook, curiosity, stakes, specifics, momentum, emotion, transformation, cause, payoff, shareability, and whether it stands alone.",
  ],
  [
    "Three gates, no exceptions",
    "A moment that needs outside context, ends without a payoff, or opens flat never ships — however high it scores elsewhere.",
  ],
  [
    "It reads the whole conversation first",
    "So a clip can start before the line you'd search for, and end after the laugh lands.",
  ],
  [
    "The best line often isn't first",
    "When it sits mid-clip, we play it up front, then rewind — so viewers stay to see how it got there.",
  ],
  [
    "Reactions beat monologues",
    "In the breakout Shorts we studied, the other person's disbelief is usually the payoff. We extend the cut to catch it.",
  ],
  [
    "Median viral clip: 45 seconds",
    "From 84 breakout podcast Shorts. We aim for 20-45s and charge every second past 45.",
  ],
];

export function WhileYouWait() {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;
    const timer = window.setInterval(() => setI((n) => (n + 1) % WHILE_YOU_WAIT.length), 6000);
    return () => window.clearInterval(timer);
  }, []);
  const [title, body] = WHILE_YOU_WAIT[i] as [string, string];

  return (
    <section className="mt-8 rounded-[1.75rem] bg-surface p-6 ring-1 ring-line sm:p-7">
      <p className="text-xs font-bold tracking-widest text-blue uppercase">While it reads</p>
      <div key={i} className="animate-pop mt-3">
        <h3 className="display-heavy text-xl sm:text-2xl">{title}</h3>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">{body}</p>
      </div>
      <div className="mt-5 flex gap-1.5" aria-hidden>
        {WHILE_YOU_WAIT.map((item, k) => (
          <span
            key={item[0]}
            className={`h-1 flex-1 rounded-full ${k === i ? "bg-blue" : "bg-sunken"}`}
          />
        ))}
      </div>
    </section>
  );
}

/** Placeholder cards where the picked moments will appear. */
export function MomentPlaceholders() {
  return (
    <section className="mt-10" aria-label="Moments on the way">
      <h2 className="display-heavy text-2xl">Your best moments land here</h2>
      <div className="mt-5 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="animate-shimmer overflow-hidden rounded-[1.75rem] bg-surface ring-1 ring-line"
            style={{ animationDelay: `${i * 0.25}s` }}
          >
            <div className={`video-tone-${i + 1} aspect-video`} />
            <div className="space-y-3 p-5">
              <div className="h-4 w-3/4 rounded-full bg-sunken" />
              <div className="h-3 w-1/2 rounded-full bg-blue-soft" />
              <div className="h-3 w-5/6 rounded-full bg-sunken" />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
