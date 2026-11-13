/** Vertical list of the real pipeline stages and their status (PRD §6-D, no fake progress). */
import { Check, X } from "lucide-react";

import { Spinner } from "@/components/ui/spinner";
import { PIPELINE_STEPS, type StepStatus } from "@/lib/project-state";

const DOT: Record<StepStatus, string> = {
  done: "bg-blue text-white",
  current: "bg-lime text-ink",
  failed: "bg-danger text-white",
  pending: "border border-line-strong",
};

export function StageTimeline({ statuses }: { statuses: StepStatus[] }) {
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
            <span className={`grid size-6 shrink-0 place-items-center rounded-full ${DOT[status]}`}>
              {status === "done" ? <Check className="size-3.5" aria-hidden /> : null}
              {status === "failed" ? <X className="size-3.5" aria-hidden /> : null}
              {status === "current" ? (
                <Spinner className="size-3.5" label={`${step.label} in progress`} />
              ) : null}
            </span>
            <span className={status === "pending" ? "text-muted" : "font-medium"}>
              {step.label}
              {status === "failed" ? <span className="sr-only"> (failed)</span> : null}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
