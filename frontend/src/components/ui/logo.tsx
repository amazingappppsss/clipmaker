/**
 * Clip2Easy wordmark: two chunky pills — "CLIP" + a lime "2EASY" tag.
 * `tone="light"` for use on blue backgrounds, `"dark"` on white.
 */
import Link from "next/link";

export function Logo({ href = "/", tone = "dark" }: { href?: string; tone?: "dark" | "light" }) {
  return (
    <Link
      href={href}
      aria-label="Clip2Easy home"
      className="inline-flex items-center font-display text-[13px] font-black tracking-wide uppercase [font-stretch:115%]"
    >
      <span
        className={`rounded-full px-3 py-1.5 ${
          tone === "light" ? "bg-white text-ink" : "bg-ink text-white"
        }`}
      >
        Clip
      </span>
      <span className="-ml-1.5 -rotate-3 rounded-full rounded-bl-none border-2 border-ink bg-lime px-2.5 py-1 text-ink">
        2Easy
      </span>
    </Link>
  );
}
