/** Three-step explanation of the product (PRD §4). */
import { Download, UploadCloud, Wand2 } from "lucide-react";

const STEPS = [
  {
    Icon: UploadCloud,
    title: "Upload your video",
    body: "Drop in a podcast, interview or lesson. Defaults are smart — no setup needed.",
  },
  {
    Icon: Wand2,
    title: "AI does the editing",
    body: "It transcribes, understands the whole conversation, picks complete moments, reframes the speaker and adds captions.",
  },
  {
    Icon: Download,
    title: "Download and post",
    body: "Every clip is quality-checked before you see it, with a title, caption and hashtags ready to go.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-5xl">
        <h2 className="text-center text-3xl font-semibold tracking-tight sm:text-4xl">
          Upload. Leave.{" "}
          <span className="font-display font-normal italic">Come back to shorts.</span>
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-center text-muted">
          Processing runs in the background — close the tab and we&apos;ll keep working.
        </p>
        <ol className="mt-14 grid gap-5 md:grid-cols-3">
          {STEPS.map(({ Icon, title, body }, i) => (
            <li
              key={title}
              className="rounded-[var(--radius-card)] border border-line bg-surface p-6"
            >
              <div className="flex items-center justify-between">
                <span className="grid size-11 place-items-center rounded-xl bg-sunken">
                  <Icon className="size-5" aria-hidden />
                </span>
                <span className="font-display text-3xl text-line-strong italic">0{i + 1}</span>
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
