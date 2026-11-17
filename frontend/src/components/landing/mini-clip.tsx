/**
 * What comes back, at a glance: a 9:16 frame with captions on it.
 *
 * Drawn, not filmed. We own no gameplay footage, and a stock video of somebody else's desk
 * would say nothing — so this shows the *shape* of the output (vertical, captioned, one word
 * lit at a time, the pick's reason on it) without pretending to be a customer's clip.
 */
import { PixelSprite, type SpriteName } from "@/components/landing/pixel-sprite";

export interface MiniClipProps {
  caption: string[];
  /** Index of the word currently lit, as the burned-in captions do. */
  lit: number;
  seconds: number;
  /** Optional: left off when the same label already sits beside the clip. */
  badge?: string;
  sprite: SpriteName;
  tone: "night" | "ember" | "deep";
  className?: string;
}

const TONES: Record<MiniClipProps["tone"], string> = {
  night: "from-[#131644] via-[#2b1b5e] to-[#0b0b12]",
  ember: "from-[#3a1708] via-[#7a2a12] to-[#140a06]",
  deep: "from-[#06303a] via-[#0b5566] to-[#04161c]",
};

export function MiniClip({
  caption,
  lit,
  seconds,
  badge,
  sprite,
  tone,
  className = "",
}: MiniClipProps) {
  return (
    <div
      className={`relative aspect-[9/16] overflow-hidden rounded-2xl border-2 border-ink bg-gradient-to-b ${TONES[tone]} ${className}`}
    >
      {/* A suggestion of a scene: bands of light, not a picture of anybody. */}
      <div className="absolute inset-x-0 top-0 h-1/2 bg-[radial-gradient(60%_60%_at_50%_0%,rgb(255_255_255/0.22),transparent_70%)]" />
      <div className="absolute inset-x-0 bottom-1/3 h-px bg-white/20" />

      {badge ? (
        <span className="absolute top-2 left-2 inline-flex items-center gap-1 rounded-full bg-black/55 px-2 py-0.5 text-[0.55rem] font-semibold text-white backdrop-blur-sm">
          <PixelSprite name={sprite} className="size-2.5" />
          {badge}
        </span>
      ) : (
        <span className="absolute top-2 left-2 grid size-5 place-items-center rounded-full bg-black/55 backdrop-blur-sm">
          <PixelSprite name={sprite} className="size-2.5" />
        </span>
      )}
      <span className="absolute top-2 right-2 rounded-full bg-black/55 px-2 py-0.5 font-mono text-[0.55rem] text-white">
        0:{String(seconds).padStart(2, "0")}
      </span>

      {/* The captions: big, centred low, one word lit — the way they are burned in. */}
      <p className="absolute right-2 bottom-7 left-2 text-center font-display text-[0.8rem] leading-tight font-black uppercase">
        {caption.map((word, i) => (
          <span
            key={`${word}-${i}`}
            className={
              i === lit
                ? "mx-[1px] inline-block rounded bg-lime px-1 text-ink"
                : "mx-[1px] inline-block text-white [text-shadow:0_2px_0_rgb(0_0_0/0.55)]"
            }
          >
            {word}
          </span>
        ))}
      </p>

      <span className="absolute inset-x-2 bottom-3 h-1 rounded-full bg-white/25">
        <span className="block h-full w-2/3 rounded-full bg-lime" />
      </span>
    </div>
  );
}
