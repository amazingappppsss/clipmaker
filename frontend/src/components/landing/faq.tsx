/** Answers to the questions that stop people from trying it. */
const QA: Array<[string, string]> = [
  [
    "Do I need to edit anything?",
    "No. Clips come out cut, captioned, framed vertically on whoever is talking, with a hook title. Download and post. You can still copy the title, caption and hashtags we wrote.",
  ],
  [
    "What videos work best?",
    "Conversations: podcasts, interviews, panels, lessons and talking-head videos, up to 4 hours long. The more people talk, the better the clips.",
  ],
  [
    "How long does it take?",
    "A few minutes for most videos. It runs in the background, so you can close the tab and come back.",
  ],
  [
    "How do credits work?",
    "1 credit = 1 minute of video, with no hidden multipliers. If processing fails, your credits come back automatically. You get 15 free minutes to try it.",
  ],
  [
    "Can I use any YouTube video?",
    "Only videos you own or have permission to use. Clip2Easy is built for creators repurposing their own content.",
  ],
];

export function Faq() {
  return (
    <section aria-labelledby="faq-heading" className="px-4 pt-24 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <h2 id="faq-heading" className="display-heavy text-center text-4xl sm:text-5xl">
          Questions
        </h2>
        <div className="mt-10 space-y-3">
          {QA.map(([q, a]) => (
            <details key={q} className="group rounded-2xl bg-surface p-5 ring-1 ring-line">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-bold">
                {q}
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-lime text-lg transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-muted">{a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
