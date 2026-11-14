/**
 * Why our picks beat "random sentences": the STOP · STAY · SHARE framework, and what it
 * replaces (an editor's hours). Claims here are about our method, not invented metrics.
 */
const PILLARS = [
  {
    tag: "STOP",
    title: "Hooks in the first 3 seconds",
    body: "Every clip opens on a question, a bold claim or a number. If the best line is mid-clip, it plays first as a flash-forward.",
  },
  {
    tag: "STAY",
    title: "No dead air. No filler.",
    body: "Real stakes, specific details and the funny or emotional peaks. Pauses are cut, but never the beat before a reveal.",
  },
  {
    tag: "SHARE",
    title: "Ends on the payoff",
    body: "The punchline, the reveal, the other person's reaction. The bit people send to friends and argue about in the comments.",
  },
];

const ROWS: Array<[string, string, string]> = [
  ["Find the best moments", "Watch the whole episode", "Done for you"],
  ["Cut, crop to 9:16, follow the speaker", "1–2 hours per clip", "Automatic"],
  ["Animated captions", "Type and time every word", "Automatic"],
  ["Titles, hooks, hashtags", "Guesswork", "Written from what was said"],
  ["Cost", "$20–50 per clip for a freelancer", "From $0.10 per minute of video"],
];

export function WhyBetter() {
  return (
    <section aria-labelledby="why-heading" className="px-4 pt-24 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <h2 id="why-heading" className="display-heavy text-center text-4xl sm:text-6xl">
          Picks like an <span className="text-blue">editor</span>, not a robot
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-muted">
          Most AI clippers grab the loudest sentence. Clip2Easy follows the rules behind viral
          clips: we studied what breakout podcast Shorts actually do and turned it into a framework
          every clip has to pass.
        </p>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {PILLARS.map((p, i) => (
            <div
              key={p.tag}
              className={`rounded-[1.75rem] p-7 ${i === 1 ? "bg-blue text-white" : "bg-surface"}`}
            >
              <span
                className={`inline-block rounded-full px-3 py-1 font-display text-sm font-black ${
                  i === 1 ? "bg-lime text-ink" : "bg-ink text-lime"
                }`}
              >
                {p.tag}
              </span>
              <h3 className="display-heavy mt-5 text-xl">{p.title}</h3>
              <p
                className={`mt-2 text-sm leading-relaxed ${i === 1 ? "text-white/85" : "text-muted"}`}
              >
                {p.body}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-16 overflow-hidden rounded-[1.75rem] bg-surface ring-1 ring-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-line">
                <th className="p-4 sm:p-5" />
                <th className="p-4 font-semibold text-muted sm:p-5">Editing it yourself</th>
                <th className="bg-lime p-4 font-display font-black sm:p-5">Clip2Easy</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map(([what, diy, us]) => (
                <tr key={what} className="border-b border-line last:border-0">
                  <th scope="row" className="p-4 font-semibold sm:p-5">
                    {what}
                  </th>
                  <td className="p-4 text-muted sm:p-5">{diy}</td>
                  <td className="bg-lime/25 p-4 font-semibold sm:p-5">{us}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
