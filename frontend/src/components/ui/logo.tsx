/** ClipMaker wordmark. `tone="light"` for use on gradient/dark backgrounds. */
import Link from "next/link";

export function Logo({ href = "/", tone = "dark" }: { href?: string; tone?: "dark" | "light" }) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-2 font-display text-xl font-extrabold tracking-tight ${
        tone === "light" ? "text-white" : "text-ink"
      }`}
    >
      <span
        aria-hidden
        className={`grid size-8 place-items-center rounded-xl ${
          tone === "light" ? "bg-white" : "gradient-fill"
        } -rotate-6 shadow-sm`}
      >
        <span
          className={`h-0 w-0 translate-x-px border-y-[6px] border-l-[9px] border-y-transparent ${
            tone === "light" ? "border-l-magenta" : "border-l-white"
          }`}
        />
      </span>
      ClipMaker
    </Link>
  );
}
