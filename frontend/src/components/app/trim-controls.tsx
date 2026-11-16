"use client";

/**
 * Fixing a cut the AI got wrong.
 *
 * Our biggest gap was never a missing feature — it was that a wrong decision could not be
 * fixed at all. A clip that starts a beat late or ends before the laugh was simply unusable.
 *
 * Deliberately not a timeline scrubber: the common failure is small and directional ("it cut
 * too early"), so nudges in whole and half seconds are faster than dragging, work on a phone,
 * and cannot produce a nonsense range. The backend clamps anything odd regardless.
 */
import { Check, Loader2, RotateCcw, Scissors } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { ApiError } from "@/services/api-client";
import { correctClip } from "@/services/projects";

/** How far one press moves an edge, in seconds. */
const STEPS = [-1, -0.5, 0.5, 1];

function clock(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function TrimControls({
  projectId,
  clipId,
  start,
  end,
  disabled,
  onQueued,
}: {
  projectId: string;
  clipId: string;
  start: number;
  end: number;
  disabled?: boolean;
  onQueued?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [draftStart, setDraftStart] = useState(start);
  const [draftEnd, setDraftEnd] = useState(end);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const changed = draftStart !== start || draftEnd !== end;

  const nudge = (edge: "start" | "end", by: number) => {
    setDone(false);
    if (edge === "start") {
      // Never let the handles cross, whatever the backend would do about it.
      setDraftStart((v) => Math.max(0, Math.min(v + by, draftEnd - 2)));
    } else {
      setDraftEnd((v) => Math.max(draftStart + 2, v + by));
    }
  };

  const save = async () => {
    if (busy || !changed) return;
    setBusy(true);
    setError(null);
    try {
      await correctClip(projectId, clipId, {
        ...(draftStart !== start ? { start_seconds: Number(draftStart.toFixed(2)) } : {}),
        ...(draftEnd !== end ? { end_seconds: Number(draftEnd.toFixed(2)) } : {}),
      });
      setDone(true);
      onQueued?.();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Couldn't save that. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-full border-2 border-ink px-3 py-1 text-xs font-bold hover:bg-ink hover:text-white disabled:opacity-40"
      >
        <Scissors className="size-3.5" aria-hidden /> Fix the cut
      </button>
    );
  }

  return (
    <div className="w-full rounded-2xl bg-sunken p-4">
      <div className="flex items-center justify-between">
        <p className="font-display text-sm font-black">Fix the cut</p>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs font-semibold text-muted hover:text-ink"
        >
          Close
        </button>
      </div>

      {(["start", "end"] as const).map((edge) => {
        const value = edge === "start" ? draftStart : draftEnd;
        return (
          <div key={edge} className="mt-3 flex flex-wrap items-center gap-2">
            <span className="w-12 text-xs font-bold tracking-wide text-muted uppercase">
              {edge}
            </span>
            <span className="w-14 font-mono text-sm tabular-nums">{clock(value)}</span>
            {STEPS.map((by) => (
              <button
                key={by}
                type="button"
                onClick={() => nudge(edge, by)}
                className="rounded-full border border-line-strong bg-surface px-2.5 py-1 text-xs font-bold tabular-nums hover:border-ink"
              >
                {by > 0 ? `+${by}` : by}s
              </button>
            ))}
          </div>
        );
      })}

      <p className="mt-3 text-xs text-muted">
        New length {Math.round(draftEnd - draftStart)}s · we rebuild just this clip, free.
      </p>

      {error ? (
        <div className="mt-3">
          <Alert tone="error">{error}</Alert>
        </div>
      ) : null}

      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          onClick={save}
          disabled={busy || !changed}
          className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-1.5 text-sm font-bold text-white disabled:opacity-40"
        >
          {busy ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : done ? (
            <Check className="size-4" aria-hidden />
          ) : null}
          {busy ? "Saving" : done ? "Rebuilding" : "Rebuild this clip"}
        </button>
        {changed && !busy ? (
          <button
            type="button"
            onClick={() => {
              setDraftStart(start);
              setDraftEnd(end);
              setDone(false);
            }}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink"
          >
            <RotateCcw className="size-3.5" aria-hidden /> Reset
          </button>
        ) : null}
      </div>
    </div>
  );
}
