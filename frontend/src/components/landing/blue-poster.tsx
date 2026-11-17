/**
 * The loud block.
 *
 * The rest of the page is deliberately calm — white, lowercase, small sprites. One section
 * shouts, and this is it: cobalt, a grid, poster-scale type with cards breaking the line and
 * arrows pointing at what matters. Calm, loud, calm reads as confidence; loud all the way
 * through reads as a billboard nobody asked for.
 */
import { Squiggle } from "@/components/landing/squiggle";
import { PixelSprite } from "@/components/landing/pixel-sprite";

const CARDS = [
  {
    sprite: "speaker" as const,
    tag: "00:47:12",
    title: "the 1v4 nobody called",
    meta: "found by sound",
    rotate: "-rotate-[6deg]",
  },
  {
    sprite: "star" as const,
    tag: "03:58:44",
    title: "the crash, and the ten seconds after",
    meta: "8/8 checks passed",
    rotate: "rotate-[5deg]",
  },
];

export function BluePoster() {
  return (
    <section
      aria-labelledby="poster-heading"
      className="blue-grid relative mx-2 mt-24 overflow-hidden rounded-[2rem] px-4 py-16 sm:mx-4 sm:rounded-[2.75rem] sm:px-8 sm:py-24"
    >
      <div className="relative mx-auto max-w-6xl">
        <p className="text-center text-xs font-bold tracking-widest text-lime uppercase">
          What you get back
        </p>

        <h2
          id="poster-heading"
          className="display-heavy relative mx-auto mt-6 max-w-4xl text-center text-[clamp(2.2rem,6.6vw,5.2rem)] leading-[0.88] text-white"
        >
          <span className="block">Thirty clips.</span>
          <span className="block">
            <span className="text-lime">One</span> upload.
          </span>
          <span className="block">Zero editing.</span>
        </h2>

        {/* Cards break the type line, arrows point at them: the poster grammar. */}
        <div className="pointer-events-none absolute inset-0 hidden lg:block">
          <div className={`absolute top-[22%] -left-4 w-56 ${CARDS[0]!.rotate}`}>
            <Card {...CARDS[0]!} />
          </div>
          <Squiggle className="absolute bottom-[14%] left-[9rem] size-20 -rotate-[200deg] text-lime" variant={1} />

          <div className={`absolute -right-4 bottom-[4%] w-56 ${CARDS[1]!.rotate}`}>
            <Card {...CARDS[1]!} />
          </div>
          <Squiggle
            className="absolute right-[13rem] bottom-[6%] size-20 -scale-x-100 text-lime"
            variant={2}
          />
        </div>

        {/* On a phone the cards cannot float, so they stack under the type instead of vanishing. */}
        <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:hidden">
          {CARDS.map((card) => (
            <Card key={card.tag} {...card} />
          ))}
        </div>

        <p className="mx-auto mt-12 max-w-xl text-center text-lg leading-relaxed font-semibold text-white/85">
          Vertical, captioned, and each one carrying the reason it was picked. The weak ones
          never reach you — that is the whole job.
        </p>
      </div>
    </section>
  );
}

function Card({
  sprite,
  tag,
  title,
  meta,
}: {
  sprite: "speaker" | "star";
  tag: string;
  title: string;
  meta: string;
}) {
  return (
    <div className="rounded-2xl border-2 border-ink bg-white p-4 shadow-[6px_6px_0_0_var(--color-ink)]">
      <div className="flex items-center gap-2">
        <PixelSprite name={sprite} className="size-4" />
        <span className="font-mono text-[0.7rem] text-muted">{tag}</span>
      </div>
      <p className="mt-2 text-base leading-snug font-semibold text-ink">{title}</p>
      <p className="mt-2 inline-block rounded-full bg-lime px-2.5 py-1 text-[0.7rem] font-black text-ink uppercase">
        {meta}
      </p>
    </div>
  );
}
