/**
 * A game HUD, not a feature list: the state of a VOD being scanned, in pixel type.
 *
 * It is the one place on the page that says what the product literally does — reads the
 * whole recording, including the parts nobody narrated — without a paragraph of copy.
 */

const STARS = 5;

export function VodHud({ className = "" }: { className?: string }) {
  return (
    <div
      className={`pixel-panel flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 ${className}`}
    >
      <span className="pixel text-[0.5rem] text-teal sm:text-[0.6rem]">VOD 04:12:33</span>

      <span className="flex items-center gap-2">
        <span className="pixel text-[0.5rem] text-white/60 sm:text-[0.6rem]">AUDIO</span>
        {/* The level meter: this is the signal we find a crash with. */}
        <span className="flex items-end gap-[3px]" aria-hidden>
          {[3, 6, 4, 9, 14, 7, 4, 11, 5, 3].map((h, i) => (
            <span
              key={i}
              className={`w-[4px] ${i === 4 || i === 7 ? "bg-magenta" : "bg-teal/70"}`}
              style={{ height: `${h}px` }}
            />
          ))}
        </span>
      </span>

      <span className="flex items-center gap-2">
        <span className="pixel text-[0.5rem] text-white/60 sm:text-[0.6rem]">CLIPS</span>
        <span className="flex gap-1" aria-hidden>
          {Array.from({ length: STARS }, (_, i) => (
            <span
              key={i}
              className={`size-[10px] ${i < 4 ? "bg-lime" : "bg-white/20"}`}
              style={{
                clipPath:
                  "polygon(50% 0, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)",
              }}
            />
          ))}
        </span>
      </span>

      <span className="pixel text-[0.5rem] text-lime sm:text-[0.6rem]">30 FOUND</span>
    </div>
  );
}
