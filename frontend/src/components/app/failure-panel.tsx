/**
 * Friendly failure screen: what happened in plain words, what to do next, and (for credits)
 * a meter showing exactly how far off you are. Copy comes from lib/failure.ts.
 */
import { AlertTriangle, Coins, Link2Off, RotateCcw, Wrench } from "lucide-react";

import { Button, ButtonLink } from "@/components/ui/button";
import { describeFailure, type FailureKind } from "@/lib/failure";

const ICONS: Record<FailureKind, typeof Coins> = {
  credits: Coins,
  fetch: RotateCcw,
  link: Link2Off,
  video: AlertTriangle,
  ours: Wrench,
};

function CreditMeter({ needed, have }: { needed: number; have: number }) {
  const total = Math.min(needed, 30);
  const filled = Math.min(have, total);
  return (
    <div className="mt-6">
      <div className="flex flex-wrap gap-1.5" aria-hidden>
        {Array.from({ length: total }, (_, i) => (
          <span
            key={i}
            className={`size-4 rounded-full ${i < filled ? "bg-blue" : "border-2 border-dashed border-blue/40"}`}
          />
        ))}
      </div>
      <p className="mt-2 text-sm font-semibold">
        <span className="text-blue">{have} you have</span>
        <span className="text-muted"> · {Math.max(needed - have, 0)} more needed</span>
      </p>
    </div>
  );
}

export function FailurePanel({
  code,
  message,
  onRetry,
  retrying,
}: {
  code: string | null | undefined;
  message: string | null | undefined;
  onRetry: () => void;
  retrying: boolean;
}) {
  const help = describeFailure(code, message);
  const Icon = ICONS[help.kind];
  return (
    <div className="flex flex-col items-start">
      <span className="grid size-12 place-items-center rounded-2xl bg-lime text-ink">
        <Icon className="size-6" aria-hidden />
      </span>
      <h2 className="display-heavy mt-5 text-3xl sm:text-4xl">{help.title}</h2>
      <p className="mt-3 max-w-xl text-lg text-ink-soft">{help.body}</p>
      {help.kind === "credits" && help.needed !== undefined && help.have !== undefined ? (
        <CreditMeter needed={help.needed} have={help.have} />
      ) : null}
      <div className="mt-7 flex flex-wrap items-center gap-3">
        {help.canRetry ? (
          <Button onClick={onRetry} loading={retrying} className="uppercase">
            Try again
          </Button>
        ) : null}
        <ButtonLink href={help.alt.href} variant={help.canRetry ? "secondary" : "primary"}>
          {help.alt.label}
        </ButtonLink>
      </div>
      {help.kind !== "credits" && help.kind !== "video" && message ? (
        <p className="mt-6 text-xs text-muted">Details: {message}</p>
      ) : null}
    </div>
  );
}
