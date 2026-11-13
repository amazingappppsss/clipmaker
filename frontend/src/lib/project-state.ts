/**
 * Presentation rules for project states (mirrors ProjectState in backend core/enums.py).
 * Pure and unit-tested: the UI must never claim a stage is done before the backend says so.
 */
import type { ProjectState } from "@/services/api-types";

export type StateTone = "neutral" | "active" | "success" | "warning" | "danger";

/** Processing stages in pipeline order, with user-facing labels (PRD §6-D). */
export const PIPELINE_STEPS: ReadonlyArray<{ state: ProjectState; label: string }> = [
  { state: "INGESTING", label: "Preparing video" },
  { state: "TRANSCRIBING", label: "Transcribing" },
  { state: "UNDERSTANDING", label: "Understanding video" },
  { state: "SELECTING", label: "Finding moments" },
  { state: "EDITING", label: "Editing" },
  { state: "RENDERING", label: "Rendering" },
  { state: "QUALITY_CHECK", label: "Quality checking" },
];

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

export type StepStatus = "done" | "current" | "pending";

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
