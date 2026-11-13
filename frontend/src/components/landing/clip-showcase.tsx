"use client";

/**
 * Floating phone mockups showing the *style* of output: hook title, speaker framing and
 * word-by-word animated captions. Clearly labelled as an illustration — these are not real
 * results. TECH DEBT: swap in real rendered clips once the pipeline exists (Milestone 6).
 */
import { Play } from "lucide-react";
import { useEffect, useState } from "react";

interface DemoClip {
  hook: string;
  caption: string[];
  tone: string;
  length: string;
}

const CLIPS: DemoClip[] = [
  {
    hook: "The habit that changed everything",
    caption: ["I", "stopped", "checking", "my", "phone", "first"],
    tone: "video-tone-1",
    length: "0:41",
  },
  {
    hook: "Why most startups die in year two",
    caption: ["It's", "never", "the", "product.", "It's", "focus."],
    tone: "video-tone-2",
    length: "0:58",
  },
  {
    hook: "“I almost quit — then this happened”",
    caption: ["That", "one", "email", "changed", "my", "life"],
    tone: "video-tone-3",
    length: "0:36",
  },
  {
    hook: "The 2-minute rule for hard tasks",
    caption: ["Just", "start.", "Motivation", "comes", "after", "action"],
    tone: "video-tone-4",
    length: "0:49",
  },
];

const STEP_MS = 420;

function useTicker(): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;
    const id = window.setInterval(() => setTick((t) => t + 1), STEP_MS);
    return () => window.clearInterval(id);
  }, []);
  return tick;
}

function Phone({ clip, tick, index }: { clip: DemoClip; tick: number; index: number }) {
  // Show 3 words at a time and highlight the "spoken" one, like modern creator captions.
  const active = (tick + index * 2) % clip.caption.length;
  const start = Math.floor(active / 3) * 3;
  const visible = clip.caption.slice(start, start + 3);
  return (
    <div
      className={`animate-float relative aspect-[9/16] w-52 shrink-0 snap-center overflow-hidden rounded-[2rem] border-[6px] border-ink shadow-[var(--shadow-float)] sm:w-60 ${clip.tone}`}
      style={{ animationDelay: `${index * -1.4}s` }}
    >
      {/* abstract speaker */}
      <div className="absolute inset-x-0 bottom-0 flex flex-col items-center">
        <span className="size-20 rounded-full bg-white/25" />
        <span className="mt-2 h-28 w-40 rounded-t-[5rem] bg-white/20" />
      </div>
      <div className="absolute inset-x-3 top-4 flex items-start justify-between gap-2">
        <p className="rounded-xl bg-white px-2.5 py-1.5 text-[13px] leading-tight font-extrabold text-ink shadow-sm">
          {clip.hook}
        </p>
      </div>
      <p className="absolute inset-x-2 bottom-[34%] text-center font-display text-[22px] leading-none font-extrabold text-white uppercase [text-shadow:0_2px_0_rgb(0_0_0/0.35)]">
        {visible.map((word, i) => (
          <span
            key={`${start}-${i}`}
            className={`mx-0.5 inline-block rounded-md px-1 py-0.5 transition-colors ${
              start + i === active ? "bg-sun text-ink" : ""
            }`}
          >
            {word}
          </span>
        ))}
      </p>
      <span className="absolute right-3 bottom-3 inline-flex items-center gap-1 rounded-full bg-black/50 px-2 py-1 text-xs font-semibold text-white">
        <Play className="size-3 fill-current" aria-hidden />
        {clip.length}
      </span>
    </div>
  );
}

export function ClipShowcase() {
  const tick = useTicker();
  return (
    <section aria-label="Example output style" className="relative z-10 -mt-32 sm:-mt-40">
      <div className="mx-auto max-w-6xl">
        <div className="flex snap-x snap-mandatory gap-5 overflow-x-auto px-6 pt-4 pb-8 [scrollbar-width:none] sm:justify-center sm:gap-6">
          {CLIPS.map((clip, i) => (
            <div key={clip.hook} className={i % 2 === 1 ? "sm:mt-12" : ""}>
              <Phone clip={clip} tick={tick} index={i} />
            </div>
          ))}
        </div>
        <p className="text-center text-xs font-medium text-muted">
          Illustration of the output style
        </p>
      </div>
    </section>
  );
}
