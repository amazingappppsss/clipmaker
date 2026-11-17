"use client";

/**
 * "Try it without signing up": a long example episode as a timeline. Click a highlighted
 * moment to see the short Clip2Easy makes from it — score, hook type, why it works, the
 * moment it turns. Example data, labelled as such (no real people).
 */
import { Sparkles } from "lucide-react";
import { useState } from "react";

import { PhoneClip } from "@/components/landing/phone-clip";

interface Moment {
  at: number; // position on the timeline, 0-100
  time: string;
  length: string;
  title: string;
  hook: string;
  score: number;
  why: string;
  turn: string;
  strengths: string[];
  caption: string[];
  highlight: string[];
  tone: string;
}

const MOMENTS: Moment[] = [
  {
    at: 12,
    time: "08:41",
    length: "0:38",
    title: "He quit a $400K job",
    hook: "Shocking number",
    score: 94,
    why: "Opens on a number nobody expects, then a specific story that proves it.",
    turn: "I walked out of the building and realised I'd never felt that free.",
    strengths: ["Scroll-stopping hook", "Someone changes", "Strong payoff"],
    caption: ["I", "walked", "away", "from", "$400K", "on", "a", "Tuesday."],
    highlight: ["$400K"],
    tone: "video-tone-1",
  },
  {
    at: 37,
    time: "27:05",
    length: "0:29",
    title: "The host didn't believe him",
    hook: "Reaction",
    score: 91,
    why: "A wild claim, then the host's live disbelief. The reaction is the payoff.",
    turn: "Wait — you're telling me you never once checked the account?",
    strengths: ["Emotional peak", "Made to share", "Strong payoff"],
    caption: ["Wait,", "you", "NEVER", "checked", "the", "account?"],
    highlight: ["NEVER"],
    tone: "video-tone-3",
  },
  {
    at: 58,
    time: "41:52",
    length: "0:44",
    title: "Stop saving like this",
    hook: "Warning",
    score: 86,
    why: "Calls out a common mistake and gives one concrete fix people will save.",
    turn: "Your savings account is losing you money every single month.",
    strengths: ["Real stakes", "Concrete details", "Made to share"],
    caption: ["Your", "savings", "are", "losing", "you", "money", "every", "month."],
    highlight: [],
    tone: "video-tone-2",
  },
  {
    at: 81,
    time: "58:13",
    length: "0:33",
    title: "The worst advice I ever got",
    hook: "Confession",
    score: 89,
    why: "A vulnerable admission with a twist ending: people comment their own.",
    turn: "I took the advice, and it cost me three years.",
    strengths: ["Someone changes", "Emotional peak", "Stands alone"],
    caption: ["It", "cost", "me", "three", "years", "of", "my", "life."],
    highlight: ["three"],
    tone: "video-tone-4",
  },
];

export function LiveDemo() {
  const [active, setActive] = useState(0);
  const m = MOMENTS[active] ?? MOMENTS[0]!;

  return (
    <section id="demo" aria-labelledby="demo-heading" className="scroll-mt-8 px-4 pt-24 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <p className="text-center text-xs font-bold tracking-widest text-blue uppercase">
          Try it right here
        </p>
        <h2 id="demo-heading" className="headline mt-3 text-center text-[clamp(1.9rem,4.4vw,3.2rem)]">
          A 1-hour episode <span className="text-blue">→</span> 4 bangers
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-center text-muted">
          Click a highlighted moment. This is what Clip2Easy pulls out of a long conversation, and
          exactly why.
        </p>

        <div className="mt-12 rounded-[2rem] bg-surface p-5 ring-1 ring-line sm:p-8">
          {/* the episode */}
          <div className="flex items-center justify-between text-xs font-semibold text-muted">
            <span>🎙️ The Money Talk · Ep. 42 (example)</span>
            <span className="tabular-nums">1:12:40</span>
          </div>
          <div className="relative mt-3 h-14 rounded-2xl bg-sunken">
            {/* fake waveform */}
            <div className="absolute inset-x-3 inset-y-3 flex items-center gap-[3px] opacity-40">
              {Array.from({ length: 90 }, (_, k) => (
                <span
                  key={k}
                  className="flex-1 rounded-full bg-ink"
                  style={{ height: `${25 + ((k * 37) % 70)}%` }}
                />
              ))}
            </div>
            {MOMENTS.map((x, k) => (
              <button
                key={x.time}
                type="button"
                onClick={() => setActive(k)}
                aria-pressed={k === active}
                aria-label={`Moment at ${x.time}: ${x.title}`}
                className={`absolute top-1.5 bottom-1.5 w-[7%] -translate-x-1/2 rounded-xl ring-2 transition-all ${
                  k === active
                    ? "scale-105 bg-lime ring-ink"
                    : "bg-blue/80 ring-transparent hover:bg-blue"
                }`}
                style={{ left: `${x.at}%` }}
              />
            ))}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {MOMENTS.map((x, k) => (
              <button
                key={x.time}
                type="button"
                onClick={() => setActive(k)}
                className={`rounded-full px-3 py-1 text-xs font-bold tabular-nums transition-colors ${
                  k === active ? "bg-ink text-lime" : "bg-sunken text-ink-soft hover:bg-line"
                }`}
              >
                {x.time} · {x.score}
              </button>
            ))}
          </div>

          {/* the short it becomes */}
          <div className="mt-8 grid items-center gap-8 md:grid-cols-[auto_1fr]">
            <div className="mx-auto">
              <PhoneClip
                key={m.time}
                size="lg"
                tone={m.tone}
                title={m.title}
                caption={m.caption}
                highlight={m.highlight}
                score={m.score}
                hook={m.hook}
              />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-ink px-3 py-1 font-display text-sm font-black text-lime">
                  {m.score}
                </span>
                <span className="rounded-full border-2 border-ink px-3 py-0.5 text-xs font-bold">
                  🎣 {m.hook}
                </span>
                <span className="text-xs font-semibold text-muted">
                  from {m.time} · {m.length} long
                </span>
              </div>
              <h3 className="text-2xl font-semibold tracking-[-0.02em]">{m.title}</h3>
              <div className="mt-5 rounded-2xl bg-blue-soft p-4">
                <p className="text-[0.7rem] font-bold tracking-widest text-blue uppercase">
                  Why it works
                </p>
                <p className="mt-1 text-sm">{m.why}</p>
                <ul className="mt-3 flex flex-wrap gap-1.5">
                  {m.strengths.map((s) => (
                    <li
                      key={s}
                      className="rounded-full bg-lime px-2.5 py-0.5 text-xs font-bold text-ink"
                    >
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
              <blockquote className="mt-4 border-l-4 border-lime pl-3 text-sm text-ink-soft italic">
                <span className="mb-0.5 block text-[0.7rem] font-bold tracking-widest text-muted not-italic uppercase">
                  The moment it turns
                </span>
                “{m.turn}”
              </blockquote>
              <p className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-blue">
                <Sparkles className="size-4" aria-hidden />
                Cut tight, captioned, framed on the speaker, ready to post.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
