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
    <section id="features" className="scroll-mt-8 px-4 py-24 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <h2 className="display-heavy text-center text-4xl sm:text-6xl">
          An editor, <span className="rounded-2xl bg-lime px-3">minus</span> the editing
        </h2>
        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ITEMS.map(({ Icon, title, body }) => (
            <div
              key={title}
              className="rounded-[1.75rem] bg-surface p-7 transition-transform hover:-translate-y-1"
            >
              <span className="grid size-12 place-items-center rounded-2xl bg-blue text-white">
                <Icon className="size-5" aria-hidden />
              </span>
              <h3 className="display-heavy mt-6 text-lg">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
