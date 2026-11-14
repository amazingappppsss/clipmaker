import { describe, expect, it } from "vitest";

import { creditShortfall, describeFailure } from "@/lib/failure";

describe("describeFailure", () => {
  it("explains a credit shortfall with exact numbers", () => {
    const help = describeFailure(
      "insufficient_credits",
      "This video needs 5 credits but you have 2.",
    );
    expect(help.kind).toBe("credits");
    expect([help.needed, help.have]).toEqual([5, 2]);
    expect(help.body).toContain("Nothing was charged");
    expect(help.alt.href).toBe("/#pricing");
  });

  it("recognises a shortfall from the message alone (older runs)", () => {
    expect(
      creditShortfall("This video needs 12 credits but you have 0."),
    ).toEqual({ needed: 12, have: 0 });
    expect(
      describeFailure(null, "This video needs 1 credit but you have 0.").kind,
    ).toBe("credits");
  });

  it("offers upload when YouTube blocks the download", () => {
    const help = describeFailure("source_blocked", "blocked");
    expect(help.canRetry).toBe(true);
    expect(help.alt.href).toBe("/new");
  });

  it("doesn't offer a pointless retry for unusable videos", () => {
    expect(
      describeFailure("too_short", "Video is too short (minimum 30 s).")
        .canRetry,
    ).toBe(false);
    expect(describeFailure("source_private", "private").canRetry).toBe(false);
  });

  it("owns unexpected errors", () => {
    expect(describeFailure("internal_error", "boom").title).toBe(
      "That's on us",
    );
  });
});
