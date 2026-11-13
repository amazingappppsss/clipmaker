/** What the editing engine does (PRD §5). */
import { Brain, Captions, Crop, Scissors, ShieldCheck, Type } from "lucide-react";

const ITEMS = [
  {
    Icon: Brain,
    title: "Understands the whole video",
    body: "Reads the full conversation first, so every clip has context — not random sentences.",
  },
  {
    Icon: Scissors,
    title: "Never cuts mid-sentence",
    body: "Each clip opens strong and lands its point, with dead air trimmed.",
  },
  {
    Icon: Crop,
    title: "Speaker-aware framing",
    body: "Finds faces and keeps the speaker centred in a steady 9:16 frame.",
  },
  {
    Icon: Captions,
    title: "Animated captions",
    body: "Word-synced captions people actually read, inside every platform's safe zone.",
  },
  {
    Icon: Type,
    title: "Honest hooks & titles",
    body: "Titles and social captions that match what was actually said.",
  },
  {
    Icon: ShieldCheck,
    title: "Quality-checked",
    body: "Framing, audio, captions and duplicates are checked before you see a clip.",
  },
];

export function Capabilities() {
  return (
    <section id="features" className="scroll-mt-8 border-t border-line px-4 py-24 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-medium text-violet-bright">Features</p>
        <h2 className="mt-3 max-w-2xl text-4xl font-bold tracking-tight sm:text-5xl">
          A short-form editor, minus the editing.
        </h2>
        <div className="mt-12 grid gap-px overflow-hidden rounded-[var(--radius-card)] border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {ITEMS.map(({ Icon, title, body }) => (
            <div key={title} className="bg-surface p-7 transition-colors hover:bg-sunken">
              <Icon className="size-5 text-violet-bright" aria-hidden />
              <h3 className="mt-5 font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
