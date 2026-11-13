/**
 * Illustration of the transformation (one wide video → several vertical clips).
 * TECH DEBT: replace with real before/after outputs once the pipeline has produced them
 * (Milestone 6). It is labelled as an illustration so it never poses as real results.
 */
import { ArrowRight } from "lucide-react";

function Speaker({ tone }: { tone: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className={`size-7 rounded-full ${tone}`} />
      <span className={`mt-1 h-8 w-12 rounded-t-full ${tone} opacity-80`} />
    </div>
  );
}

const CLIPS = [
  { title: "The one habit that changed everything", tone: "bg-coral/70" },
  { title: "Why most startups fail in year two", tone: "bg-violet/70" },
  { title: "“I almost quit — then this happened”", tone: "bg-magenta/70" },
];

export function ReframeVisual() {
  return (
    <section aria-labelledby="reframe-heading" className="px-4 pb-20 sm:px-6">
      <h2 id="reframe-heading" className="sr-only">
        From one long video to many shorts
      </h2>
      <figure className="mx-auto max-w-5xl rounded-[1.75rem] border border-line bg-surface p-6 shadow-[var(--shadow-card)] sm:p-10">
        <div className="grid items-center gap-8 md:grid-cols-[1.3fr_auto_2fr]">
          <div>
            <div className="relative aspect-video overflow-hidden rounded-2xl bg-sunken">
              <div className="absolute inset-x-0 bottom-0 flex justify-around px-10">
                <Speaker tone="bg-coral/60" />
                <Speaker tone="bg-violet/60" />
              </div>
              <span className="absolute top-3 left-3 rounded-full bg-ink/80 px-2.5 py-1 text-xs font-medium text-white">
                1:12:40 · 16:9
              </span>
            </div>
            <p className="mt-3 text-sm text-muted">Your long-form video</p>
          </div>

          <ArrowRight className="mx-auto size-6 rotate-90 text-muted md:rotate-0" aria-hidden />

          <div>
            <div className="grid grid-cols-3 gap-3">
              {CLIPS.map((clip) => (
                <div
                  key={clip.title}
                  className="relative aspect-[9/16] overflow-hidden rounded-xl bg-sunken"
                >
                  <div className="absolute inset-x-0 bottom-[18%] flex justify-center">
                    <Speaker tone={clip.tone} />
                  </div>
                  <p className="absolute inset-x-2 top-3 text-[10px] leading-tight font-semibold sm:text-xs">
                    {clip.title}
                  </p>
                  <p className="absolute inset-x-2 bottom-3 text-center text-[9px] font-bold tracking-wide text-ink uppercase sm:text-[11px]">
                    and that&apos;s <span className="text-magenta">exactly</span> why
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-sm text-muted">
              Ready-to-post vertical shorts with captions & hooks
            </p>
          </div>
        </div>
        <figcaption className="mt-6 text-center text-xs text-muted">Illustration</figcaption>
      </figure>
    </section>
  );
}
