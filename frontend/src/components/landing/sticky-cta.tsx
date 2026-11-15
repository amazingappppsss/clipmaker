"use client";

/**
 * The input follows you down the page. Intent peaks while someone is watching the demo,
 * not when they finally reach the bottom, so the bar appears as soon as the hero's own
 * input scrolls out of view and leaves with the footer CTA.
 */
import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";

export function StickyCta() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      const past = window.scrollY > window.innerHeight * 0.9;
      const nearEnd =
        window.scrollY + window.innerHeight > document.documentElement.scrollHeight - 1100;
      setShow(past && !nearEnd);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-40 px-3 pb-3 transition-all duration-300 sm:px-4 sm:pb-4 ${
        show ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-6 opacity-0"
      }`}
      aria-hidden={!show}
    >
      <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-center gap-x-5 gap-y-2 rounded-full border-2 border-ink bg-white px-5 py-3 shadow-float sm:justify-between sm:px-6">
        <p className="text-sm font-semibold">
          Got an episode? <span className="text-muted">15 free minutes, no card.</span>
        </p>
        <a
          href="#top"
          className="inline-flex items-center gap-2 rounded-full bg-lime px-5 py-2 font-display text-sm font-black whitespace-nowrap text-ink uppercase transition-transform hover:scale-105"
          tabIndex={show ? 0 : -1}
        >
          Get clips free
          <ArrowRight className="size-4" aria-hidden />
        </a>
      </div>
    </div>
  );
}
