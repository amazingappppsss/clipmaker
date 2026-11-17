/** What the editing engine does (PRD §5). */
import { Activity, Brain, Captions, Crop, Scissors, ShieldCheck } from "lucide-react";

const ITEMS = [
  {
    Icon: Brain,
    title: "Reads the whole episode first",
    body: "Understands the full conversation, so every clip has context, a turn and a payoff. Not random sentences.",
  },
  {
    Icon: Activity,
    title: "Finds moments by sound too",
    body: "A crash, a clutch or a jumpscare has no quotable line in it. We measure the sound of the recording, so the moments nobody narrated still get found.",
  },
  {
    Icon: Crop,
    title: "Follows whoever is talking",
    body: "Hears who is speaking, finds their face, and holds the frame on them in 9:16 — moving only when the floor actually changes hands.",
  },
  {
    Icon: Captions,
    title: "Captions that pop",
    body: "Big, bold, word by word. The spoken word lights up, and numbers and names stay highlighted.",
  },
  {
    Icon: Scissors,
    title: "Cut tight, never rushed",
    body: "Dead air and filler gone. The pause before a reveal stays, and every clip ends after the laugh lands.",
  },
  {
    Icon: ShieldCheck,
    title: "Tells you why it works",
    body: "Every clip shows its score, its hook type and why it'll stop the scroll. Each one is quality-checked before download.",
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
