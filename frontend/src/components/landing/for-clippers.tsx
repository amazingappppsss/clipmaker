/**
 * Why a clipper should use this rather than any of the others — the persuasion section.
 *
 * Every claim here is something the engine actually does, and most of them name the mechanism
 * so they can be checked: the sound measurement (editing/energy.py), the hard gates
 * (pipeline/selection.py), the report card (editing/report.py), per-clip trims
 * (services/corrections.py). Nothing here is a metric we made up.
 */
import { Activity, Crop, Gauge, Hand, ListChecks, Scissors } from "lucide-react";

const REASONS = [
  {
    Icon: Activity,
    tag: "Nobody else does this",
    title: "It hears the crash. It doesn't need you to narrate it.",
    body: "Every other clipper reads the transcript, so a wipeout, a clutch 1v4 or a jumpscare is invisible to it — nothing quotable was said. We measure the sound of your VOD and judge those moments on what happens, not on what was said about it.",
  },
  {
    Icon: Gauge,
    tag: "It says no",
    title: "Three real clips, not ten padded ones",
    body: "Every moment has to clear a hard bar before it ships. A quiet session gives you fewer clips on purpose — because posting filler is what actually kills a channel, and we would rather hand you three you'd post than ten you'd delete.",
  },
  {
    Icon: Crop,
    tag: "Vertical, properly",
    title: "Reframed to 9:16, following whoever is talking",
    body: "Not a centre crop that cuts your facecam in half. It finds the face that is speaking and holds the frame there, moving only when the floor actually changes hands.",
  },
  {
    Icon: Scissors,
    tag: "Tight",
    title: "Dead air and every “um” gone",
    body: "Silences cut, filler words removed, captions burned in word by word. The beat before a reveal stays — that pause is the clip.",
  },
  {
    Icon: ListChecks,
    tag: "Receipts",
    title: "Every clip arrives with a report card",
    body: "Length, dead air, pace, leftover filler, caption coverage, how long one frame is held, whether it opens cold or ends mid-sentence. Passed or missed, in plain words. No “virality score” we cannot show you the working for.",
  },
  {
    Icon: Hand,
    tag: "Your call",
    title: "Wrong cut? Drag the ends and re-render",
    body: "You know your own moment better than any model does. Fix one clip's in and out points and only that clip is rebuilt — no new charge, no running the whole VOD again.",
  },
];

export function ForClippers() {
  return (
    <section
      aria-labelledby="clippers-heading"
      className="sunset-grid relative mx-2 mt-20 overflow-hidden rounded-[2rem] px-4 py-20 sm:mx-4 sm:rounded-[2.75rem] sm:px-8 sm:py-24"
    >
      <div className="relative mx-auto max-w-6xl">
        <p className="text-center text-xs font-bold tracking-widest text-teal uppercase">
          Why clippers should use it
        </p>
        <h2
          id="clippers-heading"
          className="display-heavy mt-4 text-center text-4xl text-white sm:text-6xl"
        >
          Built for the <span className="neon">five-hour VOD</span>,
          <br className="hidden sm:block" /> not the podcast interview
        </h2>
        <p className="mx-auto mt-5 max-w-2xl text-center text-base leading-relaxed text-white/75">
          Gameplay carries its payoff in the picture. Clippers built for talking heads miss the
          whole thing — so we stopped judging your VOD only by what came out of your mouth.
        </p>

        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {REASONS.map(({ Icon, tag, title, body }) => (
            <div
              key={title}
              className="rounded-[1.75rem] bg-white/[0.06] p-7 ring-1 ring-white/15 backdrop-blur-sm transition-transform hover:-translate-y-1"
            >
              <span className="grid size-11 place-items-center rounded-2xl bg-magenta text-white">
                <Icon className="size-5" aria-hidden />
              </span>
              <p className="mt-5 text-[0.7rem] font-bold tracking-widest text-teal uppercase">
                {tag}
              </p>
              <h3 className="display-heavy mt-2 text-lg text-white sm:text-xl">{title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-white/70">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
