"use client";

/**
 * Project page: real status from the backend, polled while processing, plus source facts.
 * Clip results render here once the pipeline produces them (Milestone 2+).
 */
import { ArrowLeft, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { StageTimeline } from "@/components/app/stage-timeline";
import { StateBadge } from "@/components/app/state-badge";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatBytes, formatDate, formatDuration } from "@/lib/format";
import { isProcessing } from "@/lib/project-state";
import { ApiError } from "@/services/api-client";
import type { Project } from "@/services/api-types";
import { deleteProject, getProject } from "@/services/projects";

const POLL_MS = 4000;

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 font-medium tabular-nums">{value}</dd>
    </div>
  );
}

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const refresh = useCallback(
    async (signal?: AbortSignal): Promise<void> => {
      try {
        setProject(await getProject(id, signal));
        setError(null);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(
          err instanceof ApiError
            ? { code: err.code, message: err.message }
            : { code: "unknown", message: "Couldn't load this project." },
        );
      }
    },
    [id],
  );

  useEffect(() => {
    const controller = new AbortController();
    // State is set only after the request resolves (external-system sync), not synchronously.
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

  const onDelete = async (): Promise<void> => {
    if (!window.confirm("Delete this project and all of its files? This can't be undone.")) return;
    setDeleting(true);
    try {
      await deleteProject(id);
      router.push("/dashboard");
    } catch (err) {
      setError({
        code: "delete_failed",
        message: err instanceof ApiError ? err.message : "Delete failed.",
      });
      setDeleting(false);
    }
  };

  if (error?.code === "not_found") {
    return (
      <div className="py-20 text-center">
        <h1 className="text-2xl font-semibold">Project not found</h1>
        <ButtonLink href="/dashboard" variant="secondary" className="mt-6">
          Back to projects
        </ButtonLink>
      </div>
    );
  }
  if (!project) {
    return error ? (
      <Alert tone="error">{error.message}</Alert>
    ) : (
      <div className="flex justify-center py-20 text-muted">
        <Spinner />
      </div>
    );
  }

  const src = project.source_video;
  const uploadFailed = src?.upload_status === "failed";

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
          <h1 className="truncate text-4xl font-extrabold tracking-tight">{project.title}</h1>
          <div className="mt-2 flex items-center gap-3 text-sm text-muted">
            <StateBadge state={project.state} />
            <span>Created {formatDate(project.created_at)}</span>
          </div>
        </div>
        <Button variant="danger" size="sm" onClick={() => void onDelete()} loading={deleting}>
          <Trash2 className="size-4" aria-hidden /> Delete
        </Button>
      </div>

      {error ? (
        <div className="mt-6">
          <Alert tone="error">{error.message}</Alert>
        </div>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_20rem]">
        <section className="rounded-[var(--radius-card)] border border-line bg-surface p-6">
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
            <div>
              <h2 className="text-lg font-semibold">Video uploaded and verified</h2>
              <p className="mt-1 text-sm text-muted">
                Automatic clip generation isn&apos;t switched on for this server yet. Your video is
                stored privately and will be processed once it is.
              </p>
            </div>
          ) : project.error_message ? (
            <Alert tone={project.state === "NEEDS_REVIEW" ? "info" : "error"}>
              {project.error_message}
            </Alert>
          ) : (
            <p className="text-muted">
              Your clips will appear here as soon as they pass quality checks.
            </p>
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

        <aside className="rounded-[var(--radius-card)] border border-line bg-surface p-4">
          <h2 className="px-2 pt-1 pb-2 text-sm font-semibold">Processing</h2>
          <StageTimeline state={project.state} />
        </aside>
      </div>
    </div>
  );
}
