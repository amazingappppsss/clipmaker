"use client";

/**
 * Project page: one clear action per state, real progress from the backend, and results.
 *   UPLOADED     → "Find my clips" (shows the credit cost)
 *   processing   → live stage timeline (polled), safe to close the tab
 *   FAILED       → reason + "Try again" (resumes from the failed stage; credits were refunded)
 *   NEEDS_REVIEW / COMPLETED → the picked moments
 */
import { ArrowLeft, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { MomentCard } from "@/components/app/moment-card";
import { StageTimeline } from "@/components/app/stage-timeline";
import { StateBadge } from "@/components/app/state-badge";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatBytes, formatDate, formatDuration } from "@/lib/format";
import { isProcessing, stepStatuses, stepStatusesFromJob } from "@/lib/project-state";
import { ApiError } from "@/services/api-client";
import type { Clip, JobStatus, Project } from "@/services/api-types";
import {
  deleteProject,
  getClips,
  getProject,
  getStatus,
  startProcessing,
} from "@/services/projects";

const POLL_MS = 3000;
const RESULT_STATES = new Set(["NEEDS_REVIEW", "COMPLETED"]);

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

function errorText(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"start" | "delete" | null>(null);

  const refresh = useCallback(
    async (signal?: AbortSignal): Promise<void> => {
      try {
        const [p, s] = await Promise.all([getProject(id, signal), getStatus(id, signal)]);
        setProject(p);
        setStatus(s);
        if (RESULT_STATES.has(p.state)) setClips(await getClips(id, signal));
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (err instanceof ApiError && err.code === "not_found") setNotFound(true);
        else setError(errorText(err, "Couldn't load this project."));
      }
    },
    [id],
  );

  useEffect(() => {
    const controller = new AbortController();
    // State is set only after the requests resolve (external-system sync).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  // Poll only while the backend is actively working.
  useEffect(() => {
    if (!project || !isProcessing(project.state)) return undefined;
    const timer = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [project, refresh]);

  const onStart = async (): Promise<void> => {
    setBusy("start");
    setError(null);
    try {
      setProject(await startProcessing(id));
      await refresh();
    } catch (err) {
      setError(errorText(err, "Couldn't start processing."));
    } finally {
      setBusy(null);
    }
  };

  const onDelete = async (): Promise<void> => {
    if (!window.confirm("Delete this project and all of its files? This can't be undone.")) return;
    setBusy("delete");
    try {
      await deleteProject(id);
      router.push("/dashboard");
    } catch (err) {
      setError(errorText(err, "Delete failed."));
      setBusy(null);
    }
  };

  if (notFound) {
    return (
      <div className="py-20 text-center">
        <h1 className="display-heavy text-3xl">Project not found</h1>
        <ButtonLink href="/dashboard" variant="secondary" className="mt-6">
          Back to projects
        </ButtonLink>
      </div>
    );
  }
  if (!project) {
    return error ? (
      <Alert tone="error">{error}</Alert>
    ) : (
      <div className="flex justify-center py-20 text-muted">
        <Spinner />
      </div>
    );
  }

  const src = project.source_video;
  const uploadFailed = src?.upload_status === "failed";
  const credits = src?.duration_seconds ? Math.max(1, Math.ceil(src.duration_seconds / 60)) : null;
  const processing = isProcessing(project.state);
  const steps = status ? stepStatusesFromJob(status.stages) : stepStatuses(project.state);

  return (
    <div>
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"
      >
        <ArrowLeft className="size-4" aria-hidden /> Projects
      </Link>
      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="display-heavy truncate text-4xl">{project.title}</h1>
          <div className="mt-3 flex items-center gap-3 text-sm text-muted">
            <StateBadge state={project.state} />
            <span>Created {formatDate(project.created_at)}</span>
          </div>
        </div>
        <Button
          variant="danger"
          size="sm"
          onClick={() => void onDelete()}
          loading={busy === "delete"}
          disabled={processing}
          title={processing ? "Wait for processing to finish" : undefined}
        >
          <Trash2 className="size-4" aria-hidden /> Delete
        </Button>
      </div>

      {error ? (
        <div className="mt-6">
          <Alert tone="error">{error}</Alert>
        </div>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_20rem]">
        <section className="rounded-[1.75rem] bg-surface p-6 ring-1 ring-line sm:p-8">
          {uploadFailed ? (
            <>
              <Alert tone="error">
                {src?.error_message ?? "The upload could not be verified."}
              </Alert>
              <ButtonLink href="/new" className="mt-5">
                Upload another video
              </ButtonLink>
            </>
          ) : project.state === "CREATED" ? (
            <p className="text-muted">This project has no verified video yet.</p>
          ) : project.state === "UPLOADED" ? (
            <div className="flex flex-col items-start gap-4">
              <h2 className="display-heavy text-2xl">Ready to find your best moments</h2>
              <p className="text-muted">
                We&apos;ll transcribe the whole video, understand the conversation and pick the
                moments that work as standalone shorts.
              </p>
              <Button
                size="lg"
                className="uppercase"
                onClick={() => void onStart()}
                loading={busy === "start"}
              >
                <Sparkles className="size-5" aria-hidden /> Find my clips
              </Button>
              {credits ? (
                <p className="text-xs text-muted">
                  Uses {credits} credit{credits === 1 ? "" : "s"} (1 per minute of video)
                </p>
              ) : null}
            </div>
          ) : processing ? (
            <div>
              <h2 className="display-heavy text-2xl">Working on it…</h2>
              <p className="mt-2 text-muted">
                This runs in the background — you can close this tab and come back later.
              </p>
            </div>
          ) : project.state === "FAILED" ? (
            <div className="flex flex-col items-start gap-4">
              <Alert tone="error">{project.error_message ?? "Processing failed."}</Alert>
              <Button
                onClick={() => void onStart()}
                loading={busy === "start"}
                className="uppercase"
              >
                Try again
              </Button>
            </div>
          ) : (
            <div>
              <h2 className="display-heavy text-2xl">
                {clips.length} best moment{clips.length === 1 ? "" : "s"} found
              </h2>
              {project.error_message ? (
                <div className="mt-3">
                  <Alert tone="info">{project.error_message}</Alert>
                </div>
              ) : null}
            </div>
          )}

          {src && !uploadFailed ? (
            <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-line pt-6 sm:grid-cols-4">
              <Fact label="Duration" value={formatDuration(src.duration_seconds)} />
              <Fact
                label="Resolution"
                value={src.width && src.height ? `${src.width}×${src.height}` : "—"}
              />
              <Fact label="File size" value={formatBytes(src.size_bytes)} />
              <Fact label="Audio" value={src.has_audio ? "Yes" : "—"} />
            </dl>
          ) : null}
        </section>

        <aside className="rounded-[1.75rem] bg-surface p-4 ring-1 ring-line">
          <h2 className="px-2 pt-1 pb-2 text-sm font-bold">Processing</h2>
          <StageTimeline statuses={steps} />
        </aside>
      </div>

      {clips.length ? (
        <section className="mt-10" aria-label="Picked moments">
          <div className="grid gap-6 md:grid-cols-2">
            {clips.map((clip) => (
              <MomentCard key={clip.id} clip={clip} sourceUrl={project.source_video_url ?? null} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
