/** Three-step explanation of the product (PRD §4), as bold color-blocked cards. */
import { Download, UploadCloud, Wand2 } from "lucide-react";

const STEPS = [
  {
    Icon: UploadCloud,
    title: "Drop your video",
    body: "Podcast, interview, lesson — up to 4 hours. Smart defaults, zero setup.",
    tone: "bg-magenta",
  },
  {
    Icon: Wand2,
    title: "AI edits it",
    body: "Transcribes, understands the whole conversation, picks complete moments, frames the speaker, adds captions.",
    tone: "bg-violet",
  },
  {
    Icon: Download,
    title: "Post your shorts",
    body: "Every clip is quality-checked, with a title, caption and hashtags ready to go.",
    tone: "bg-coral",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-8 px-4 py-24 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <p className="text-center text-sm font-bold tracking-widest text-magenta uppercase">
          How it works
        </p>
        <h2 className="mx-auto mt-3 max-w-3xl text-center text-4xl font-extrabold tracking-tight sm:text-6xl">
          Upload. Leave. <span className="gradient-text">Come back to shorts.</span>
        </h2>
        <p className="mx-auto mt-5 max-w-xl text-center text-lg text-muted">
          Processing runs in the background — close the tab and we&apos;ll keep working.
        </p>
        <ol className="mt-14 grid gap-5 md:grid-cols-3">
          {STEPS.map(({ Icon, title, body, tone }, i) => (
            <li
              key={title}
              className={`relative overflow-hidden rounded-[2rem] p-8 text-white ${tone} transition-transform hover:-translate-y-1`}
            >
              <span
                aria-hidden
                className="absolute -top-6 -right-2 font-display text-[9rem] leading-none font-extrabold text-white/15"
              >
                {i + 1}
              </span>
              <span className="grid size-14 place-items-center rounded-2xl bg-white/20">
                <Icon className="size-6" aria-hidden />
              </span>
              <h3 className="mt-10 text-2xl font-extrabold">{title}</h3>
              <p className="mt-2 leading-relaxed text-white/85">{body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
