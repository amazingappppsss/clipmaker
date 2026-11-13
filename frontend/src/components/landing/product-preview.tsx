"use client";

/**
 * App-window mockup: a source video with detected moments on its timeline, and the finished
 * vertical clips (animated word-by-word captions, titles, QA badge, download).
 * Clearly labelled as an illustration — not real output.
 * TECH DEBT: replace with real rendered clips once the pipeline exists (Milestone 6).
 */
import { CheckCircle2, Download, Play } from "lucide-react";
import { useEffect, useState } from "react";

interface DemoClip {
  title: string;
  words: string[];
  tone: string;
  length: string;
}

const CLIPS: DemoClip[] = [
  {
    title: "The habit that changed everything",
    words: ["I", "stopped", "checking", "my", "phone", "first"],
    tone: "video-tone-1",
    length: "0:41",
  },
  {
    title: "Why most startups die in year two",
    words: ["It's", "never", "the", "product.", "It's", "focus."],
    tone: "video-tone-2",
    length: "0:58",
  },
  {
    title: "I almost quit — then this happened",
    words: ["That", "one", "email", "changed", "my", "life"],
    tone: "video-tone-3",
    length: "0:36",
  },
  {
    title: "The 2-minute rule for hard tasks",
    words: ["Just", "start.", "Motivation", "comes", "after", "action"],
    tone: "video-tone-4",
    length: "0:49",
  },
];

/** Timeline segments (percent of the source) that became clips. */
const MOMENTS = [
  { left: 8, width: 6 },
  { left: 27, width: 8 },
  { left: 51, width: 5 },
  { left: 74, width: 7 },
];

const STEP_MS = 450;

function useTicker(): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;
    const id = window.setInterval(() => setTick((t) => t + 1), STEP_MS);
    return () => window.clearInterval(id);
  }, []);
  return tick;
}

function Speaker() {
  return (
    <div aria-hidden className="absolute inset-x-0 bottom-0 flex flex-col items-center">
      <span className="size-[28%] rounded-full bg-white/15" style={{ aspectRatio: "1" }} />
      <span className="mt-1 h-[34%] w-[62%] rounded-t-full bg-white/10" style={{ minHeight: 40 }} />
    </div>
  );
}

function ClipCard({ clip, tick, index }: { clip: DemoClip; tick: number; index: number }) {
  const active = (tick + index * 2) % clip.words.length;
  const start = Math.floor(active / 3) * 3;
  const visible = clip.words.slice(start, start + 3);
  return (
    <div className="w-40 shrink-0 snap-start sm:w-auto">
      <div
        className={`relative aspect-[9/16] overflow-hidden rounded-xl ring-1 ring-white/10 ${clip.tone}`}
      >
        <Speaker />
        <p className="absolute inset-x-1.5 bottom-[30%] text-center font-display text-[15px] leading-tight font-extrabold text-white uppercase [text-shadow:0_2px_6px_rgb(0_0_0/0.6)] sm:text-base">
          {visible.map((word, i) => (
            <span
              key={`${start}-${i}`}
              className={`mx-[2px] inline-block ${start + i === active ? "text-lime" : ""}`}
            >
              {word}
            </span>
          ))}
        </p>
        <span className="absolute top-2 left-2 inline-flex items-center gap-1 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-semibold text-white">
          <Play className="size-2.5 fill-current" aria-hidden />
          {clip.length}
        </span>
      </div>
      <p className="mt-2.5 line-clamp-2 text-[13px] leading-snug font-medium text-ink">
        {clip.title}
      </p>
      <div className="mt-2 flex items-center justify-between">
        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-success">
          <CheckCircle2 className="size-3" aria-hidden /> QA passed
        </span>
        <span className="grid size-6 place-items-center rounded-md bg-sunken text-muted">
          <Download className="size-3" aria-hidden />
        </span>
      </div>
    </div>
  );
}

export function ProductPreview() {
  const tick = useTicker();
  return (
    <figure className="relative">
      <div
        aria-hidden
        className="absolute inset-x-0 -top-6 bottom-6 -z-10 rounded-[3rem] bg-blue/10 blur-3xl"
      />
      <div className="overflow-hidden rounded-[1.75rem] border-2 border-ink bg-surface shadow-[8px_8px_0_0_var(--color-ink)]">
        {/* window chrome */}
        <div className="flex items-center gap-2 border-b border-line px-4 py-3">
          <span className="size-2.5 rounded-full bg-line-strong" />
          <span className="size-2.5 rounded-full bg-line-strong" />
          <span className="size-2.5 rounded-full bg-line-strong" />
          <p className="ml-3 truncate text-xs text-muted">
            Podcast ep. 42 — 1:12:40 · <span className="text-ink-soft">4 clips ready</span>
          </p>
        </div>

        <div className="grid gap-6 p-4 sm:p-6 lg:grid-cols-[1fr_1.55fr]">
          {/* source */}
          <div className="min-w-0">
            <p className="mb-3 text-xs font-medium tracking-wide text-muted uppercase">Source</p>
            <div className="video-tone-2 relative aspect-video overflow-hidden rounded-xl ring-1 ring-white/10">
              <div aria-hidden className="absolute inset-x-0 bottom-0 flex justify-around px-[12%]">
                <span className="flex flex-col items-center">
                  <span className="size-9 rounded-full bg-white/15 sm:size-11" />
                  <span className="mt-1 h-10 w-16 rounded-t-full bg-white/10 sm:h-14 sm:w-20" />
                </span>
                <span className="flex flex-col items-center">
                  <span className="size-9 rounded-full bg-white/15 sm:size-11" />
                  <span className="mt-1 h-10 w-16 rounded-t-full bg-white/10 sm:h-14 sm:w-20" />
                </span>
              </div>
              <span className="absolute top-2 left-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                16:9
              </span>
            </div>
            <div className="relative mt-4 h-8 rounded-lg bg-sunken" aria-label="Detected moments">
              <div
                aria-hidden
                className="absolute inset-y-[38%] right-2 left-2 rounded-full bg-[repeating-linear-gradient(90deg,var(--color-line-strong)_0_2px,transparent_2px_5px)]"
              />
              {MOMENTS.map((m) => (
                <span
                  key={m.left}
                  className="absolute inset-y-1 rounded-md bg-blue ring-2 ring-lime"
                  style={{ left: `${m.left}%`, width: `${m.width}%` }}
                />
              ))}
            </div>
            <div className="mt-4 space-y-2 text-xs leading-relaxed text-muted">
              <p>
                <span className="font-medium text-ink-soft">Topics:</span> habits, startups, focus,
                burnout
              </p>
              <p>
                <span className="font-medium text-ink-soft">Picked:</span> 4 complete moments with a
                strong opening and a clear payoff
              </p>
            </div>
          </div>

          {/* clips */}
          <div className="min-w-0">
            <p className="mb-3 text-xs font-medium tracking-wide text-muted uppercase">Shorts</p>
            <div className="flex snap-x gap-3 overflow-x-auto pb-1 [scrollbar-width:none] sm:grid sm:grid-cols-4 sm:overflow-visible">
              {CLIPS.map((clip, i) => (
                <ClipCard key={clip.title} clip={clip} tick={tick} index={i} />
              ))}
            </div>
          </div>
        </div>
      </div>
      <figcaption className="mt-3 text-center text-xs text-muted">Illustration</figcaption>
    </figure>
  );
}
