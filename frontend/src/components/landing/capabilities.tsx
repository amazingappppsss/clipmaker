/** What the editing engine does (PRD §5), as a colorful bento grid. */
import { Brain, Captions, Crop, Scissors, ShieldCheck, Type } from "lucide-react";

const ITEMS = [
  {
    Icon: Brain,
    title: "Understands the whole video",
    body: "Reads the full conversation first, so every clip has context — not random sentences.",
    span: "md:col-span-2",
    style: "bg-ink text-white",
    icon: "gradient-fill text-white",
  },
  {
    Icon: Scissors,
    title: "Never cuts mid-sentence",
    body: "Each clip opens strong and lands its point.",
    span: "",
    style: "bg-sun text-ink",
    icon: "bg-ink text-sun",
  },
  {
    Icon: Crop,
    title: "Speaker-aware framing",
    body: "Finds faces and keeps the speaker centred in a steady 9:16 frame.",
    span: "",
    style: "bg-surface",
    icon: "bg-blue text-white",
  },
  {
    Icon: Captions,
    title: "Captions people actually read",
    body: "Word-synced, punchy, animated — inside safe margins on every platform.",
    span: "md:col-span-2",
    style: "bg-violet text-white",
    icon: "bg-white text-violet",
  },
  {
    Icon: Type,
    title: "Honest hooks & titles",
    body: "Titles that match what was actually said. No invented claims.",
    span: "md:col-span-2",
    style: "bg-surface",
    icon: "bg-magenta text-white",
  },
  {
    Icon: ShieldCheck,
    title: "Quality-checked",
    body: "Framing, audio, captions and duplicates are checked before you see a clip.",
    span: "",
    style: "bg-coral text-white",
    icon: "bg-white text-coral",
  },
];

export function Capabilities() {
  return (
    <section id="features" className="scroll-mt-8 px-4 pb-24 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-bold tracking-widest text-violet uppercase">Features</p>
        <h2 className="mt-3 max-w-3xl text-4xl font-extrabold tracking-tight sm:text-6xl">
          A short-form editor, <span className="gradient-text">minus the editing.</span>
        </h2>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {ITEMS.map(({ Icon, title, body, span, style, icon }) => (
            <div
              key={title}
              className={`rounded-[2rem] p-7 ring-1 ring-line transition-transform hover:-translate-y-1 ${span} ${style}`}
            >
              <span className={`grid size-12 place-items-center rounded-2xl ${icon}`}>
                <Icon className="size-5" aria-hidden />
              </span>
              <h3 className="mt-8 text-2xl font-extrabold">{title}</h3>
              <p className="mt-2 max-w-md leading-relaxed opacity-80">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
