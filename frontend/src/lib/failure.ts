/**
 * Turns a failed run's code + message into friendly, specific help. Pure and unit-tested.
 * The backend's message stays the source of truth; this only chooses tone and next steps.
 */
export type FailureKind = "credits" | "fetch" | "link" | "video" | "ours";

export interface FailureHelp {
  kind: FailureKind;
  title: string;
  body: string;
  /** Show "Try again" (resumes the run) — false when retrying can't change the outcome. */
  canRetry: boolean;
  /** Secondary action. */
  alt: { label: string; href: string };
  needed?: number;
  have?: number;
}

const FETCH = new Set([
  "source_blocked",
  "source_network",
  "source_failed",
  "importer_unavailable",
]);
const LINK = new Set([
  "source_private",
  "source_restricted",
  "source_unavailable",
  "unsupported_url",
]);
const VIDEO = new Set([
  "too_short",
  "too_long",
  "no_audio",
  "no_speech",
  "media_unreadable",
  "unreadable_video",
]);

/** "This video needs 5 credits but you have 2." → { needed: 5, have: 2 } */
export function creditShortfall(
  message: string | null | undefined,
): { needed: number; have: number } | null {
  const m = message?.match(/needs (\d+) credits? but you have (\d+)/i);
  return m ? { needed: Number(m[1]), have: Number(m[2]) } : null;
}

export function describeFailure(
  code: string | null | undefined,
  message: string | null | undefined,
): FailureHelp {
  const shortfall = creditShortfall(message);
  if (code === "insufficient_credits" || shortfall) {
    const needed = shortfall?.needed;
    const have = shortfall?.have;
    return {
      kind: "credits",
      title: "Almost there",
      body:
        needed !== undefined && have !== undefined
          ? `This video needs ${needed} credits (1 per minute) and you have ${have}. Nothing was charged. Top up, then hit Try again.`
          : "You don't have enough credits for this video yet. Nothing was charged.",
      canRetry: true,
      alt: { label: "See plans", href: "/#pricing" },
      needed,
      have,
    };
  }
  if (code && FETCH.has(code)) {
    return {
      kind: "fetch",
      title: "YouTube didn't hand it over",
      body: "Downloads sometimes get blocked for a little while. Try again in a minute, or upload the file instead.",
      canRetry: true,
      alt: { label: "Upload the file", href: "/new" },
    };
  }
  if (code && LINK.has(code)) {
    return {
      kind: "link",
      title: "We can't open that video",
      body: "It may be private, age-restricted, removed or not a supported link. Try a different video.",
      canRetry: false,
      alt: { label: "Try another video", href: "/new" },
    };
  }
  if (code && VIDEO.has(code)) {
    return {
      kind: "video",
      title: "This video won't work",
      body: message ?? "We couldn't use this video.",
      canRetry: false,
      alt: { label: "Try another video", href: "/new" },
    };
  }
  return {
    kind: "ours",
    title: "That's on us",
    body: "Something went wrong on our side, not yours. Your credits are safe. Trying again usually fixes it.",
    canRetry: true,
    alt: { label: "Start a new project", href: "/new" },
  };
}
