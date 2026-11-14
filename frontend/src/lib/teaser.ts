/**
 * Flash-forward playback for a clip preview: play the teaser line first, flash "rewind",
 * then play the clip from its start and stop at its end. Pure and unit-tested.
 */
export type Phase = "teaser" | "main" | "done";

export interface ClipTiming {
  start: number;
  end: number;
  teaserStart?: number | null;
  teaserEnd?: number | null;
}

export function hasTeaser(t: ClipTiming): boolean {
  return t.teaserStart != null && t.teaserEnd != null && t.teaserEnd > t.teaserStart;
}

/** Where playback begins: the teaser if there is one, else the clip start. */
export function initialPlayback(t: ClipTiming): { phase: Phase; at: number } {
  return hasTeaser(t)
    ? { phase: "teaser", at: t.teaserStart as number }
    : { phase: "main", at: t.start };
}

/**
 * What to do at playback time `now`: keep going (null), jump somewhere, or stop.
 * `rewind` marks the jump from the teaser back to the clip start (show the flash).
 */
export function nextPlayback(
  phase: Phase,
  now: number,
  t: ClipTiming,
): { phase: Phase; seekTo?: number; rewind?: boolean; pause?: boolean } | null {
  if (phase === "teaser" && now >= (t.teaserEnd as number)) {
    return { phase: "main", seekTo: t.start, rewind: true };
  }
  if (phase === "main" && now >= t.end) return { phase: "done", pause: true };
  return null;
}
