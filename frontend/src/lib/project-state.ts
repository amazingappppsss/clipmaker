/**
 * Presentation rules for project states (mirrors ProjectState in backend core/enums.py).
 * Pure and unit-tested: the UI must never claim a stage is done before the backend says so.
 */
import type { ProjectState, StageStatus } from "@/services/api-types";

export type StateTone = "neutral" | "active" | "success" | "warning" | "danger";

/** Processing stages in pipeline order, with user-facing labels (PRD §6-D). */
export const PIPELINE_STEPS: ReadonlyArray<{ state: ProjectState; label: string; soon?: true }> = [
  { state: "INGESTING", label: "Preparing video" },
  { state: "TRANSCRIBING", label: "Transcribing" },
  { state: "UNDERSTANDING", label: "Understanding video" },
  { state: "SELECTING", label: "Finding moments" },
  { state: "EDITING", label: "Editing" },
  { state: "RENDERING", label: "Rendering" },
  { state: "QUALITY_CHECK", label: "Quality checking" },
];

/** The stages that actually run today. */
export const LIVE_STEPS = PIPELINE_STEPS.filter((s) => !s.soon);

/** Headline and one-line explanation for the stage that is running (describes real work). */
export function stepCopy(
  state: ProjectState,
  fromLink: boolean,
): { title: string; detail: string } {
  switch (state) {
    case "INGESTING":
      return fromLink
        ? {
            title: "Fetching your video",
            detail: "Downloading it, checking the audio and pulling out a clean speech track.",
          }
        : {
            title: "Preparing your video",
            detail: "Checking the file and pulling out a clean speech track.",
          };
    case "TRANSCRIBING":
      return {
        title: "Listening to every word",
        detail: "A word-by-word transcript with timestamps and who's speaking.",
      };
    case "UNDERSTANDING":
      return {
        title: "Understanding the story",
        detail: "AI reads the whole conversation: the topics, the speakers, the big ideas.",
      };
    case "SELECTING":
      return {
        title: "Picking the best moments",
        detail: "Scoring every candidate on hook, payoff, emotion and whether it stands alone.",
      };
    case "EDITING":
      return {
        title: "Editing like a pro",
        detail: "Cutting dead air, adding the flash-forward hook and framing whoever is talking.",
      };
    case "RENDERING":
      return {
        title: "Rendering your shorts",
        detail: "Vertical 1080×1920 with animated captions, punch-in zooms and studio-level audio.",
      };
    case "QUALITY_CHECK":
      return {
        title: "Final quality check",
        detail: "Every clip is checked before you can download it. Nearly there.",
      };
    default:
      return { title: "Working on it", detail: "Your video is being processed." };
  }
}

/** Index (in LIVE_STEPS) of the stage running now, from the real step statuses; -1 if none. */
export function currentLiveStep(statuses: StepStatus[]): number {
  const live = statuses.slice(0, LIVE_STEPS.length);
  const running = live.indexOf("current");
  if (running >= 0) return running;
  const firstPending = live.indexOf("pending");
  return firstPending;
}

/** "m:ss" (or "h:mm:ss") between an ISO start time and now; "" when not started. */
export function elapsedLabel(startedAt: string | null | undefined, now: number): string {
  if (!startedAt) return "";
  const total = Math.max(0, Math.floor((now - Date.parse(startedAt)) / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = String(total % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${m}:${s}`;
}

const LABELS: Record<ProjectState, string> = {
  CREATED: "Awaiting upload",
  UPLOADED: "Uploaded",
  INGESTING: "Preparing",
  TRANSCRIBING: "Transcribing",
  UNDERSTANDING: "Understanding",
  SELECTING: "Finding moments",
  EDITING: "Editing",
  RENDERING: "Rendering",
  QUALITY_CHECK: "Quality check",
  COMPLETED: "Ready",
  NEEDS_REVIEW: "Needs review",
  FAILED: "Failed",
  CANCELLED: "Cancelled",
};

export function stateLabel(state: ProjectState): string {
  return LABELS[state];
}

export function stateTone(state: ProjectState): StateTone {
  if (state === "COMPLETED") return "success";
  if (state === "NEEDS_REVIEW") return "warning";
  if (state === "FAILED") return "danger";
  if (state === "CREATED" || state === "UPLOADED" || state === "CANCELLED") return "neutral";
  return "active";
}

/** True while the backend is working on the project (the UI should poll). */
export function isProcessing(state: ProjectState): boolean {
  return stateTone(state) === "active";
}

export type StepStatus = "done" | "current" | "pending" | "failed";

/**
 * Status of each pipeline step for a given project state.
 * Terminal states: COMPLETED/NEEDS_REVIEW mark everything done; FAILED/CANCELLED keep
 * steps pending because we do not know (from state alone) how far the run got.
 */
export function stepStatuses(state: ProjectState): StepStatus[] {
  if (state === "COMPLETED" || state === "NEEDS_REVIEW") return PIPELINE_STEPS.map(() => "done");
  const index = PIPELINE_STEPS.findIndex((s) => s.state === state);
  return PIPELINE_STEPS.map((_, i) =>
    index < 0 ? "pending" : i < index ? "done" : i === index ? "current" : "pending",
  );
}

/** Step statuses from the backend's real per-stage records (preferred over `stepStatuses`). */
export function stepStatusesFromJob(stages: StageStatus[]): StepStatus[] {
  const byStage = new Map(stages.map((s) => [s.stage, s.status]));
  return PIPELINE_STEPS.map(({ state }) => {
    const status = byStage.get(state);
    if (status === "done") return "done";
    if (status === "running") return "current";
    if (status === "failed") return "failed";
    return "pending";
  });
}
