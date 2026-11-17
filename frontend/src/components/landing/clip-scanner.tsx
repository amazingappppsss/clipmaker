"use client";

/**
 * The hero's centrepiece: the thing we do, happening.
 *
 * A stock video of a podcast told a visitor nothing — it could have been anybody's page. This
 * shows the actual claim instead: a long recording, a scan running across its sound, and the
 * moments lighting up where it got loud — including ones where nobody said a word. Clicking a
 * spike opens that clip, so the page is something to poke at rather than watch.
 *
 * The waveform and the finds are a scripted demo, labelled as one. The rules behind them are
 * real: a moment is a stretch well above the recording's own median loudness
 * (editing/energy.py), and a clip has to pass eight checks (editing/report.py).
 */
import { useEffect, useRef, useState } from "react";

import { PixelSprite } from "@/components/landing/pixel-sprite";
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion";

const BARS = 96;
const SWEEP_MS = 9000;

interface Find {
  /** Position along the recording, 0-1. */
  at: number;
  time: string;
  kind: "sound" | "words";
  title: string;
  note: string;
  seconds: number;
}

const FINDS: Find[] = [
  {
    at: 0.19,
    time: "00:47:12",
    kind: "sound",
    title: "the 1v4 nobody called",
    note: "Loud for 6s, +14 dB over your baseline. Nothing quotable was said — the clip is what happened.",
    seconds: 38,
  },
  {
    at: 0.46,
    time: "02:41:08",
    kind: "words",
    title: "“i have never seen that happen”",
    note: "Opens on a full sentence, lands on the reaction. Caption coverage 94%.",
    seconds: 52,
  },
  {
    at: 0.72,
    time: "03:58:44",
    kind: "sound",
    title: "the crash, and the ten seconds after",
    note: "The wind-up and the laughing are both in it. That part is the clip, not the impact.",
    seconds: 41,
  },
];

/** Deterministic waveform: same picture every render, no hydration mismatch. */
function heights(): number[] {
  return Array.from({ length: BARS }, (_, i) => {
    const base = 18 + Math.sin(i * 0.7) * 6 + Math.sin(i * 0.23) * 9;
    const near = FINDS.reduce((peak, f) => {
      const distance = Math.abs(i / BARS - f.at);
      return Math.max(peak, distance < 0.035 ? (1 - distance / 0.035) * 62 : 0);
    }, 0);
    return Math.max(6, Math.round(base + near));
  });
}

const HEIGHTS = heights();

export function ClipScanner() {
  const still = usePrefersReducedMotion();
  const [progress, setProgress] = useState(still ? 1 : 0);
  const [picked, setPicked] = useState<number | null>(still ? 0 : null);
  const frame = useRef<number | null>(null);

  // The sweep stops for good once somebody clicks: they are reading, not watching.
  useEffect(() => {
    if (still || picked !== null) return;
    const started = performance.now();
    const tick = (now: number) => {
      const next = Math.min(1, (now - started) / SWEEP_MS);
      setProgress(next);
      if (next < 1) frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    };
  }, [still, picked]);

  const found = FINDS.filter((f) => f.at <= progress);
  const open = picked === null ? null : FINDS[picked];

  return (
    <div className="rounded-[2rem] bg-gradient-to-br from-lime via-blue to-magenta p-[3px] shadow-float">
      <div className="overflow-hidden rounded-[1.9rem] bg-white">
        {/* Window chrome, so it reads as the app and not as an illustration. */}
        <div className="flex items-center gap-3 border-b border-line px-4 py-3">
          <span className="flex gap-1.5" aria-hidden>
            <span className="size-2.5 rounded-full bg-[#ff5f57]" />
            <span className="size-2.5 rounded-full bg-[#febc2e]" />
            <span className="size-2.5 rounded-full bg-[#28c840]" />
          </span>
          <p className="truncate font-mono text-xs text-muted">
            stream_vod_final.mp4 · 4:12:33
          </p>
          <span className="ml-auto hidden font-mono text-[0.7rem] text-muted sm:block">
            {progress < 1 ? "listening…" : "done"}
          </span>
        </div>

        <div className="px-4 pt-6 pb-5 sm:px-7">
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-sm font-semibold text-ink">
              {found.length} moment{found.length === 1 ? "" : "s"} worth clipping
            </p>
            <p className="text-xs text-muted">click a spike</p>
          </div>

          {/* The recording, as sound. */}
          <div className="relative mt-4 h-24 sm:h-28">
            <div className="flex h-full items-end gap-[2px]">
              {HEIGHTS.map((h, i) => {
                const reached = i / BARS <= progress;
                const inFind = FINDS.some((f) => Math.abs(i / BARS - f.at) < 0.035);
                return (
                  <span
                    key={i}
                    className={`flex-1 rounded-[1px] transition-colors duration-300 ${
                      !reached
                        ? "bg-line-strong"
                        : inFind
                          ? "bg-magenta"
                          : "bg-ink/35"
                    }`}
                    style={{ height: `${h}%` }}
                  />
                );
              })}
            </div>

            {/* Where the scan has got to. */}
            {progress < 1 ? (
              <span
                aria-hidden
                className="absolute top-0 bottom-0 w-[2px] bg-blue"
                style={{ left: `${progress * 100}%` }}
              />
            ) : null}

            {/* The finds themselves, popping in as the scan reaches them. */}
            {FINDS.map((f, i) =>
              f.at <= progress ? (
                <button
                  key={f.time}
                  type="button"
                  onClick={() => setPicked(i)}
                  style={{ left: `${f.at * 100}%` }}
                  className={`animate-pop absolute -top-3 -translate-x-1/2 rounded-full border-2 px-2.5 py-1 font-mono text-[0.65rem] whitespace-nowrap transition-transform hover:scale-105 ${
                    picked === i
                      ? "border-ink bg-ink text-white"
                      : "border-ink bg-white text-ink"
                  }`}
                >
                  {f.time}
                </button>
              ) : null,
            )}
          </div>

          {/* What was found there. */}
          <div className="mt-6 min-h-[8.5rem] rounded-2xl bg-sunken p-4 sm:p-5">
            {open ? (
              <div className="animate-pop">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-ink px-2.5 py-1 text-[0.7rem] font-bold text-white uppercase">
                    <PixelSprite
                      name={open.kind === "sound" ? "speaker" : "clapper"}
                      className="size-3.5"
                    />
                    {open.kind === "sound" ? "found by sound" : "found in the words"}
                  </span>
                  <span className="rounded-full bg-white px-2.5 py-1 text-[0.7rem] font-semibold text-muted">
                    {open.seconds}s · 9:16 · captions burned in
                  </span>
                  <span className="rounded-full bg-lime px-2.5 py-1 text-[0.7rem] font-black text-ink">
                    8/8 checks
                  </span>
                </div>
                <p className="mt-3 text-lg leading-snug font-semibold text-ink">{open.title}</p>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{open.note}</p>
              </div>
            ) : (
              <div className="flex h-full flex-col justify-center">
                <p className="text-sm leading-relaxed text-muted">
                  Reading the whole recording — the sound as well as the words. A spike well
                  above your own baseline is a moment, whether or not anybody narrated it.
                </p>
              </div>
            )}
          </div>

          <p className="mt-3 text-center text-xs text-muted">
            A scripted demo of the real interface. The rules behind it ship in the product.
          </p>
        </div>
      </div>
    </div>
  );
}
