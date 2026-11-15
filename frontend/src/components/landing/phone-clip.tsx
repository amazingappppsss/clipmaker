"use client";

/**
 * A phone showing exactly what Clip2Easy outputs: the lime hook title, word-by-word captions
 * with the spoken word lit up, a score badge and the hook type.
 *
 * Give it `src` and it plays that real rendered short instead (muted, looping) — the
 * captions are already burned into the file. Without `src` it falls back to the
 * illustration, whose caption cycles on its own. Motion is skipped for reduced-motion users.
 */
import { useEffect, useState } from "react";

export interface PhoneClipProps {
  title: string;
  caption: string[]; // the words, in order
  highlight?: string[]; // words always shown in lime (numbers, names)
  score: number;
  hook: string;
  tone: string; // video-tone-* background, and the poster colour behind a real video
  src?: string; // a real rendered short (MP4/WebM) to play instead of the illustration
  className?: string;
  size?: "sm" | "lg";
}

const WINDOW = 3; // words on screen at once, like the real captions

export function PhoneClip({
  title,
  caption,
  highlight = [],
  score,
  hook,
  tone,
  src,
  className = "",
  size = "sm",
}: PhoneClipProps) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (src) return undefined;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;
    const timer = window.setInterval(() => setI((n) => (n + 1) % caption.length), 420);
    return () => window.clearInterval(timer);
  }, [caption.length, src]);

  const start = Math.floor(i / WINDOW) * WINDOW;
  const words = caption.slice(start, start + WINDOW);
  const big = size === "lg";

  return (
    <div
      aria-hidden
      className={`rounded-[2rem] bg-ink p-1.5 shadow-[0_30px_60px_-20px_rgb(5_10_60/0.7)] ring-1 ring-white/20 ${big ? "w-72 sm:w-80" : "w-[11.25rem] xl:w-[12.5rem]"} ${className}`}
    >
      <div className={`relative aspect-[9/16] overflow-hidden rounded-[1.6rem] ${tone}`}>
        {src ? (
          <video
            className="absolute inset-0 size-full object-cover"
            src={src}
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
          />
        ) : null}
        {/* speaker silhouette */}
        {src ? null : (
          <>
            <span className="absolute bottom-0 left-1/2 h-[40%] w-[72%] -translate-x-1/2 rounded-t-full bg-white/15" />
            <span className="absolute bottom-[37%] left-1/2 size-[30%] -translate-x-1/2 rounded-full bg-white/20" />
          </>
        )}
        {/* hook title, like the real render */}
        {src ? null : (
          <span
            className={`absolute inset-x-3 top-[9%] rounded-md bg-lime px-1.5 py-1 text-center font-display leading-tight font-black text-ink uppercase ${big ? "text-[15px]" : "text-[10px]"}`}
          >
            {title}
          </span>
        )}
        {/* score — a real render carries its own, so don't draw a second one over it */}
        {src ? null : (
          <span
            className={`absolute top-2 right-2 rounded-full bg-ink/80 px-1.5 font-display font-black text-lime tabular-nums ${big ? "text-sm" : "text-[11px]"}`}
          >
            {score}
          </span>
        )}
        {/* captions: the spoken word pops in lime */}
        {src ? null : (
          <span
            className={`absolute inset-x-2 bottom-[24%] text-center font-display leading-none font-black text-white uppercase [text-shadow:0_2px_0_#000,0_0_8px_rgb(0_0_0/0.6)] ${big ? "text-2xl" : "text-[14px]"}`}
          >
            {words.map((w, k) => {
              const active = start + k === i;
              const lit = active || highlight.includes(w);
              return (
                <span
                  key={`${start + k}-${w}`}
                  className={`mx-[0.15em] inline-block transition-transform duration-150 ${lit ? "text-lime" : ""} ${active ? "scale-110" : ""}`}
                >
                  {w}
                </span>
              );
            })}
          </span>
        )}
        {/* progress */}
        {src ? null : (
          <span className="absolute inset-x-3 bottom-3 h-1 overflow-hidden rounded-full bg-white/25">
            <span
              className="block h-full bg-lime transition-[width] duration-300"
              style={{ width: `${((i + 1) / caption.length) * 100}%` }}
            />
          </span>
        )}
      </div>
      <p
        className={`mt-1.5 mb-0.5 text-center font-bold text-white ${big ? "text-sm" : "text-[11px]"}`}
      >
        🎣 {hook}
      </p>
    </div>
  );
}
