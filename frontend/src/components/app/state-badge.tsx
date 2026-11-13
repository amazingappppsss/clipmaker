/** Colored pill showing a project's state. */
import { stateLabel, stateTone, type StateTone } from "@/lib/project-state";
import type { ProjectState } from "@/services/api-types";

const TONE_CLASSES: Record<StateTone, string> = {
  neutral: "bg-sunken text-ink-soft",
  active: "bg-info-soft text-blue",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
};

export function StateBadge({ state }: { state: ProjectState }) {
  const tone = stateTone(state);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${TONE_CLASSES[tone]}`}
    >
      {tone === "active" ? (
        <span className="size-1.5 animate-pulse rounded-full bg-current" aria-hidden />
      ) : null}
      {stateLabel(state)}
    </span>
  );
}
