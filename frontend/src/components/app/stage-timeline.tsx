/** Vertical list of the real pipeline stages and their status (PRD §6-D, no fake progress). */
import { Check } from "lucide-react";

import { Spinner } from "@/components/ui/spinner";
import { PIPELINE_STEPS, stepStatuses } from "@/lib/project-state";
import type { ProjectState } from "@/services/api-types";

export function StageTimeline({ state }: { state: ProjectState }) {
  const statuses = stepStatuses(state);
  return (
    <ol className="space-y-1" aria-label="Processing stages">
      {PIPELINE_STEPS.map((step, i) => {
        const status = statuses[i] ?? "pending";
        return (
          <li
            key={step.state}
            className="flex items-center gap-3 rounded-lg px-2 py-2"
            aria-current={status === "current" ? "step" : undefined}
          >
            <span
              className={`grid size-6 shrink-0 place-items-center rounded-full ${
                status === "done"
                  ? "bg-success text-white"
                  : status === "current"
                    ? "bg-info-soft text-violet"
                    : "border border-line-strong"
              }`}
            >
              {status === "done" ? <Check className="size-3.5" aria-hidden /> : null}
              {status === "current" ? (
                <Spinner className="size-3.5" label={`${step.label} in progress`} />
              ) : null}
            </span>
            <span className={status === "pending" ? "text-muted" : "font-medium"}>
              {step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
