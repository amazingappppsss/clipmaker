/** What the editing engine does (PRD §5) — framed as outcomes, not jargon. */
import { Brain, Captions, Crop, Scissors, ShieldCheck, Type } from "lucide-react";

const ITEMS = [
  {
    Icon: Brain,
    title: "Understands the whole video",
    body: "Reads the full conversation first, so clips have context — not random sentences.",
  },
  {
    Icon: Scissors,
    title: "Natural start and end",
    body: "Never cuts mid-sentence. Each clip opens strong and lands its point.",
  },
  {
    Icon: Crop,
    title: "Speaker-aware framing",
    body: "Finds faces and keeps the speaker centred in a steady 9:16 frame.",
  },
  {
    Icon: Captions,
    title: "Accurate captions",
    body: "Word-synced subtitles with clean line breaks, inside safe margins.",
  },
  {
    Icon: Type,
    title: "Honest hooks & titles",
    body: "Titles that match what was actually said. No invented claims.",
  },
  {
    Icon: ShieldCheck,
    title: "Quality-checked",
    body: "Every clip is checked for framing, audio, captions and duplicates before delivery.",
  },
];

export function Capabilities() {
  return (
    <section id="features" className="scroll-mt-20 bg-surface px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-5xl">
        <h2 className="max-w-3xl text-3xl font-semibold tracking-tight sm:text-4xl">
          The work of a short-form editor,{" "}
          <span className="font-display font-normal italic">done for you.</span>
        </h2>
        <div className="mt-12 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
          {ITEMS.map(({ Icon, title, body }) => (
            <div key={title}>
              <Icon className="size-5 text-magenta" aria-hidden />
              <h3 className="mt-3 font-semibold">{title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
