/** Rotating circular "get clips free" badge (links to sign-up). */
import Link from "next/link";
import { useId } from "react";

import { Squiggle } from "@/components/landing/squiggle";

export function SpinBadge({ className = "" }: { className?: string }) {
  const text = "GET CLIPS FREE • GET CLIPS FREE •";
  // Unique per badge: the page renders more than one.
  const pathId = `badge-${useId().replace(/:/g, "")}`;
  return (
    <Link
      href="/login"
      aria-label="Get clips free"
      className={`group grid size-32 place-items-center rounded-full border-2 border-ink bg-lime text-ink shadow-[5px_5px_0_0_var(--color-ink)] transition-transform hover:scale-105 sm:size-40 ${className}`}
    >
      <svg
        viewBox="0 0 100 100"
        className="animate-spin-slow col-start-1 row-start-1 size-full"
        aria-hidden
      >
        <defs>
          <path id={pathId} d="M50,50 m-37,0 a37,37 0 1,1 74,0 a37,37 0 1,1 -74,0" />
        </defs>
        <text className="font-display text-[9.5px] font-black" fill="currentColor">
          {/* textLength ≈ circumference (2π·37 ≈ 232) so the text wraps exactly once. */}
          <textPath href={`#${pathId}`} textLength="228" lengthAdjust="spacingAndGlyphs">
            {text}
          </textPath>
        </text>
      </svg>
      <Squiggle className="col-start-1 row-start-1 size-12 sm:size-14" variant={2} />
    </Link>
  );
}
