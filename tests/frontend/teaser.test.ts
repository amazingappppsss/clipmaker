import { describe, expect, it } from "vitest";

import { hasTeaser, initialPlayback, nextPlayback } from "@/lib/teaser";

const withTeaser = { start: 10, end: 60, teaserStart: 40, teaserEnd: 43 };
const plain = { start: 10, end: 60 };

describe("flash-forward playback", () => {
  it("starts on the teaser when there is one", () => {
    expect(hasTeaser(withTeaser)).toBe(true);
    expect(initialPlayback(withTeaser)).toEqual({ phase: "teaser", at: 40 });
    expect(initialPlayback(plain)).toEqual({ phase: "main", at: 10 });
  });

  it("rewinds to the clip start after the teaser, then stops at the end", () => {
    expect(nextPlayback("teaser", 41, withTeaser)).toBeNull();
    expect(nextPlayback("teaser", 43, withTeaser)).toEqual({
      phase: "main",
      seekTo: 10,
      rewind: true,
    });
    // Passing the teaser again inside the clip is normal playback, not another jump.
    expect(nextPlayback("main", 41, withTeaser)).toBeNull();
    expect(nextPlayback("main", 60, withTeaser)).toEqual({
      phase: "done",
      pause: true,
    });
  });
});
