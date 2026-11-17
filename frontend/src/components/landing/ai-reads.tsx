"use client";

/**
 * "Watch it read." The one thing no other clipper shows: the lines the AI throws away.
 *
 * A transcript scrolls past and gets judged live — warm-up, no payoff, setup only — until a
 * line locks and becomes a short. Seeing the rejections is what makes it read as an editor
 * rather than a random-sentence grabber, and it starts on its own, so a visitor is rewarded
 * before they type anything.
 *
 * Example episodes, labelled as such: no real people, no invented metrics.
 */
import { Check, X } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";

import { PhoneClip } from "@/components/landing/phone-clip";

interface Line {
  at: string;
  text: string;
  verdict: string; // why it was thrown away, or why it locked
}

interface Episode {
  show: string;
  found: number; // moments this episode yielded, for the open loop
  skips: Line[];
  lock: Line;
  signals: Array<[string, number]>;
  clip: {
    title: string;
    caption: string[];
    highlight: string[];
    score: number;
    hook: string;
    tone: string;
  };
}

const EPISODES: Episode[] = [
  {
    show: "Founder interview · 1:42:08",
    found: 11,
    skips: [
      { at: "00:12", text: "Yeah, so — thanks for having me on, man.", verdict: "Warm-up" },
      { at: "04:31", text: "We raised a seed round in, I think, 2019?", verdict: "No stakes" },
      { at: "08:02", text: "And that's when everything changed for me.", verdict: "Setup only" },
      {
        at: "08:19",
        text: "Which, as you know, is basically what he'd said in the first place.",
        verdict: "Needs context",
      },
      { at: "08:33", text: "So anyway. Um. Where do I even start.", verdict: "Filler" },
    ],
    lock: {
      at: "08:41",
      text: "I walked away from $400K on a Tuesday. My mum didn't speak to me for a month.",
      verdict: "Hook + payoff",
    },
    signals: [
      ["Hook", 9],
      ["Stakes", 9],
      ["Payoff", 8],
    ],
    clip: {
      title: "He quit a $400K job",
      caption: ["I", "walked", "away", "from", "$400K", "on", "a", "Tuesday."],
      highlight: ["$400K"],
      score: 94,
      hook: "Shocking number",
      tone: "video-tone-1",
    },
  },
  {
    show: "Comedy podcast · 2:06:55",
    found: 14,
    skips: [
      {
        at: "19:50",
        text: "Right, so where were we — the thing about the dog.",
        verdict: "No hook",
      },
      {
        at: "24:03",
        text: "It's just, like, you have to put in the work, honestly.",
        verdict: "Too vague",
      },
      {
        at: "26:44",
        text: "So I get to the airport and I'm already late…",
        verdict: "Ends mid-story",
      },
      {
        at: "26:51",
        text: "He does the bit again — the one from last week.",
        verdict: "Needs context",
      },
      { at: "26:58", text: "And I said, no, no, no. No. Hold on.", verdict: "No payoff" },
    ],
    lock: {
      at: "27:05",
      text: "Wait — you're telling me you NEVER once checked the account? [laughter]",
      verdict: "Reaction is the payoff",
    },
    signals: [
      ["Emotion", 9],
      ["Share", 9],
      ["Hook", 8],
    ],
    clip: {
      title: "He never checked the account",
      caption: ["You", "NEVER", "checked", "the", "account?"],
      highlight: ["NEVER"],
      score: 91,
      hook: "Reaction",
      tone: "video-tone-3",
    },
  },
  {
    show: "Health interview · 58:12",
    found: 7,
    skips: [
      { at: "02:08", text: "That's a great question, and I get it a lot.", verdict: "Warm-up" },
      { at: "33:19", text: "The literature on this is genuinely mixed.", verdict: "No payoff" },
      {
        at: "41:27",
        text: "I'd been training for about six years by then.",
        verdict: "Setup only",
      },
      { at: "41:38", text: "People always ask about supplements first.", verdict: "No hook" },
      {
        at: "41:44",
        text: "And it's roughly a third of patients, give or take.",
        verdict: "Too vague",
      },
    ],
    lock: {
      at: "41:52",
      text: "I felt the heart attack start. I was 34, and I'd run a marathon that spring.",
      verdict: "Hook + turn",
    },
    signals: [
      ["Hook", 10],
      ["Emotion", 9],
      ["Standalone", 8],
    ],
    clip: {
      title: "He felt it start at 34",
      caption: ["I", "was", "34.", "I'd", "run", "a", "marathon", "that", "spring."],
      highlight: ["34."],
      score: 96,
      hook: "Confession",
      tone: "video-tone-4",
    },
  },
];

/** Reduced-motion users get the finished state, not a loop. Read, never stored in state. */
function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    (notify) => {
      const query = window.matchMedia("(prefers-reduced-motion: reduce)");
      query.addEventListener("change", notify);
      return () => query.removeEventListener("change", notify);
    },
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false,
  );
}

const SKIP_MS = 1100; // a rejected line
const LOCK_MS = 4200; // time to read the winner and watch the score land

export function AiReads() {
  // `step` walks the skips (0..n-1) and then the lock (n). `ep` rotates the episode, so a
  // visitor who keeps watching sees a different find each time — not the same canned loop.
  const [ep, setEp] = useState(0);
  const [raw, setRaw] = useState(0);
  const still = usePrefersReducedMotion();

  const episode = EPISODES[ep % EPISODES.length] as Episode;
  const total = episode.skips.length;
  const step = still ? total : raw; // held on the winning line when motion is off
  const locked = step >= total;

  useEffect(() => {
    if (still) return undefined;
    const timer = window.setTimeout(
      () => {
        if (step < total) {
          setRaw(step + 1);
        } else {
          setRaw(0);
          setEp((n) => (n + 1) % EPISODES.length);
        }
      },
      step >= total ? LOCK_MS : SKIP_MS,
    );
    return () => window.clearTimeout(timer);
  }, [ep, step, total, still]);

  const shown = episode.skips.slice(0, Math.min(step, total));

  return (
    <section aria-labelledby="reads-heading" className="px-4 pt-24 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <p className="text-center text-xs font-bold tracking-widest text-blue uppercase">
          Nobody else shows you this
        </p>
        <h2 id="reads-heading" className="headline mt-3 text-center text-[clamp(1.9rem,4.4vw,3.2rem)]">
          Watch it throw away <span className="text-blue">the bad lines</span>
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-muted">
          Every AI clipper shows you the clips it kept. Here&rsquo;s the part that actually matters
          — the hours it rejects, and the reason for each one.
        </p>

        <div className="mt-12 grid items-stretch gap-8 rounded-[2rem] bg-ink p-5 sm:p-8 lg:grid-cols-[1fr_auto]">
          {/* The transcript being judged */}
          <div className="flex min-w-0 flex-col">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/15 pb-4">
              <span className="font-display text-sm font-black tracking-wide text-white uppercase">
                {episode.show}
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-bold text-white">
                <span className="size-2 animate-pulse rounded-full bg-lime" />
                Reading the transcript
              </span>
            </div>

            <ul className="mt-5 flex flex-1 flex-col justify-center space-y-2.5" aria-live="off">
              {shown.map((line) => (
                <li
                  key={`${ep}-${line.at}`}
                  className="animate-pop flex items-start gap-3 text-sm text-white/35"
                >
                  <span className="mt-0.5 shrink-0 font-mono text-xs text-white/25">{line.at}</span>
                  <span className="min-w-0 flex-1 line-through decoration-white/25">
                    {line.text}
                  </span>
                  <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-white/10 px-2 py-0.5 text-[0.7rem] font-bold whitespace-nowrap text-white/60">
                    <X className="size-3" aria-hidden />
                    {line.verdict}
                  </span>
                </li>
              ))}

              {locked ? (
                <li className="animate-pop rounded-2xl bg-lime/15 p-4 ring-2 ring-lime">
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 shrink-0 font-mono text-xs text-lime">
                      {episode.lock.at}
                    </span>
                    <span className="min-w-0 flex-1 text-sm font-semibold text-white">
                      {episode.lock.text}
                    </span>
                    <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-lime px-2 py-0.5 text-[0.7rem] font-black whitespace-nowrap text-ink">
                      <Check className="size-3" aria-hidden />
                      {episode.lock.verdict}
                    </span>
                  </div>
                  <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
                    {episode.signals.map(([name, value]) => (
                      <span key={name} className="flex items-center gap-2">
                        <span className="text-[0.7rem] font-bold tracking-wide text-white/70 uppercase">
                          {name}
                        </span>
                        <span className="flex gap-0.5" aria-hidden>
                          {Array.from({ length: 10 }, (_, k) => (
                            <span
                              key={k}
                              className={`h-3 w-1 rounded-full ${k < value ? "bg-lime" : "bg-white/15"}`}
                            />
                          ))}
                        </span>
                        <span className="font-display text-xs font-black text-lime tabular-nums">
                          {value}
                        </span>
                      </span>
                    ))}
                  </div>
                </li>
              ) : null}
            </ul>

            <p className="mt-6 shrink-0 border-t border-white/15 pt-4 text-sm text-white/70">
              {locked ? (
                <>
                  <span className="font-display font-black text-lime">{episode.found} moments</span>{" "}
                  made the cut in this episode. This is one of them.
                </>
              ) : (
                <>
                  Scoring every moment against 11 signals, then throwing out everything that needs
                  context, opens flat or ends without a payoff.
                </>
              )}
            </p>
          </div>

          {/* What that one line becomes */}
          <div className="justify-self-center">
            <PhoneClip
              key={locked ? `${ep}-clip` : `${ep}-wait`}
              size="lg"
              tone={episode.clip.tone}
              title={locked ? episode.clip.title : "…"}
              caption={locked ? episode.clip.caption : ["Finding", "the", "moment"]}
              highlight={episode.clip.highlight}
              score={locked ? episode.clip.score : 0}
              hook={locked ? episode.clip.hook : "Scanning"}
            />
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-muted">
          {still ? "Example episodes" : "Example episodes, playing on their own"} — illustrative
          transcripts, not real people.
        </p>
      </div>
    </section>
  );
}
