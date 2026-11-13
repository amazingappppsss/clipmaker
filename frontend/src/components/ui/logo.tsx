/** ClipMaker wordmark: a vertical "clip" glyph with the brand gradient. */
import Link from "next/link";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2 font-semibold tracking-tight">
      <span
        aria-hidden
        className="relative grid h-7 w-5 place-items-center rounded-md bg-gradient-to-b from-coral via-magenta to-violet"
      >
        <span className="h-2 w-1.5 translate-x-px border-y-[4px] border-l-[6px] border-y-transparent border-l-white" />
      </span>
      <span className="text-[17px]">ClipMaker</span>
    </Link>
  );
}
