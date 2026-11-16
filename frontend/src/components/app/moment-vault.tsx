"use client";

/**
 * Every moment we scored, including the ones we didn't ship.
 *
 * Other clippers hand you N clips and keep the rest to themselves — if their AI skipped the
 * best bit of your episode, you never learn it was ever considered. We already score every
 * candidate and record why each one missed, so hiding that was never a decision, just an
 * omission.
 *
 * It answers the one question a creator cannot otherwise check: did it actually look at my
 * whole episode? And it lets them overrule us, which matters more than being right.
 */
import { ChevronDown, Loader2, Plus, Sparkles } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { ApiError } from "@/services/api-client";
import type { Moment, Moments } from "@/services/api-types";
import { promoteMoment } from "@/services/projects";

function clock(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const m = Math.floor(whole / 60);
  return `${m}:${String(whole % 60).padStart(2, "0")}`;
}

function Row({
  moment,
  projectId,
  onPromoted,
  busy,
  setBusy,
}: {
  moment: Moment;
  projectId: string;
  onPromoted: () => void;
  busy: string | null;
  setBusy: (id: string | null) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const working = busy === moment.id;

  const promote = async () => {
    if (busy) return;
    setBusy(moment.id);
    setError(null);
    try {
      await promoteMoment(projectId, moment.id);
      onPromoted();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Couldn't add that one.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <li className="border-b border-line py-3 last:border-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-display text-sm font-black tabular-nums">{moment.score}</span>
        <span className="font-mono text-xs text-muted">
          {clock(moment.start_seconds)}–{clock(moment.end_seconds)}
        </span>
        {moment.hook_type ? (
          <span className="rounded-full bg-blue-soft px-2 py-0.5 text-[0.7rem] font-bold text-blue">
            {moment.hook_type.replace(/_/g, " ")}
          </span>
        ) : null}
        {moment.selected ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-lime px-2 py-0.5 text-[0.7rem] font-black text-ink">
            <Sparkles className="size-3" aria-hidden /> shipped
          </span>
        ) : (
          <span className="text-xs text-muted">{moment.rejected_reason ?? "not shipped"}</span>
        )}
        {moment.can_promote ? (
          <button
            type="button"
            onClick={promote}
            disabled={!!busy}
            className="ml-auto inline-flex items-center gap-1 rounded-full border-2 border-ink px-2.5 py-0.5 text-xs font-bold hover:bg-ink hover:text-white disabled:opacity-40"
          >
            {working ? (
              <Loader2 className="size-3 animate-spin" aria-hidden />
            ) : (
              <Plus className="size-3" aria-hidden />
            )}
            {working ? "Adding" : "Make this a clip"}
          </button>
        ) : null}
      </div>
      {moment.transcript ? (
        <p className="mt-1.5 line-clamp-2 text-sm text-ink-soft">{moment.transcript}</p>
      ) : null}
      <p className="mt-1 text-xs text-muted">{moment.why}</p>
      {error ? (
        <div className="mt-2">
          <Alert tone="error">{error}</Alert>
        </div>
      ) : null}
    </li>
  );
}

export function MomentVault({
  data,
  projectId,
  onPromoted,
}: {
  data: Moments;
  projectId: string;
  onPromoted: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  if (!data.scanned) return null;
  const missed = data.scanned - data.shipped;

  return (
    <section className="mt-10" aria-label="Every moment we scored">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-4 rounded-[1.75rem] bg-surface p-5 text-left ring-1 ring-line hover:ring-line-strong"
      >
        <span>
          <span className="display-heavy block text-xl">
            We scanned {data.scanned} moments. {data.shipped} made the cut.
          </span>
          <span className="mt-1 block text-sm text-muted">
            {missed > 0
              ? `See the other ${missed} and why each one missed — add any of them as a clip.`
              : "Every moment that scored made it into your clips."}
          </span>
        </span>
        <ChevronDown
          className={`size-5 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>

      {open ? (
        <ul className="mt-3 rounded-[1.75rem] bg-surface px-5 ring-1 ring-line">
          {data.moments.map((moment) => (
            <Row
              key={moment.id}
              moment={moment}
              projectId={projectId}
              onPromoted={onPromoted}
              busy={busy}
              setBusy={setBusy}
            />
          ))}
        </ul>
      ) : null}
    </section>
  );
}
