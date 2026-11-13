/** Three-step explanation of the product (PRD §4). */
import { Download, UploadCloud, Wand2 } from "lucide-react";

const STEPS = [
  {
    Icon: UploadCloud,
    title: "Upload your video",
    body: "Podcast, interview, lesson — up to 4 hours. Smart defaults, zero setup.",
  },
  {
    Icon: Wand2,
    title: "AI edits it",
    body: "Transcribes, understands the whole conversation, picks complete moments, frames the speaker and adds captions.",
  },
  {
    Icon: Download,
    title: "Download and post",
    body: "Every clip is quality-checked before you see it, with a title, caption and hashtags ready.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-8 border-t border-line px-4 py-24 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-medium text-violet-bright">How it works</p>
        <h2 className="mt-3 max-w-2xl text-4xl font-bold tracking-tight sm:text-5xl">
          Upload. Leave. Come back to shorts.
        </h2>
        <p className="mt-4 max-w-xl text-muted">
          Processing runs in the background — close the tab and we&apos;ll keep working.
        </p>
        <ol className="mt-12 grid gap-4 md:grid-cols-3">
          {STEPS.map(({ Icon, title, body }, i) => (
            <li
              key={title}
              className="rounded-[var(--radius-card)] border border-line bg-surface p-6"
            >
              <div className="flex items-center justify-between">
                <span className="grid size-10 place-items-center rounded-xl bg-violet/15 text-violet-bright ring-1 ring-violet/30">
                  <Icon className="size-5" aria-hidden />
                </span>
                <span className="font-mono text-xs text-muted">0{i + 1}</span>
              </div>
              <h3 className="mt-6 text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
