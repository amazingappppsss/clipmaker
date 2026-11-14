"use client";

/** Dashboard grid card for one project, with a quick Delete (hidden while it's processing). */
import { Film, Trash2 } from "lucide-react";
import { useState } from "react";
import Link from "next/link";

import { StateBadge } from "@/components/app/state-badge";
import { formatDate, formatDuration } from "@/lib/format";
import { isProcessing } from "@/lib/project-state";
import type { Project } from "@/services/api-types";

export function ProjectCard({
  project,
  onDelete,
}: {
  project: Project;
  onDelete?: (id: string) => Promise<void>;
}) {
  const duration = project.source_video?.duration_seconds;
  const [deleting, setDeleting] = useState(false);
  const canDelete = onDelete && !isProcessing(project.state);
  return (
    <div className="relative">
      <Link
        href={`/projects/${project.id}`}
        className="group overflow-hidden rounded-[var(--radius-card)] bg-surface ring-1 ring-line transition-all hover:-translate-y-1 hover:ring-violet/50"
      >
        <div className="video-tone-1 relative aspect-video">
          {project.thumbnail_url ? (
            // Signed storage URLs are short-lived and external, so next/image optimisation does not apply.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={project.thumbnail_url} alt="" className="size-full object-cover" />
          ) : (
            <div className="grid size-full place-items-center text-white/80">
              <Film className="size-8" aria-hidden />
            </div>
          )}
          {duration ? (
            <span className="absolute right-2.5 bottom-2.5 rounded-md bg-black/70 px-1.5 py-0.5 text-xs font-medium text-white tabular-nums">
              {formatDuration(duration)}
            </span>
          ) : null}
        </div>
        <div className="p-4">
          <p className="truncate font-display text-lg font-bold">{project.title}</p>
          <div className="mt-2 flex items-center justify-between gap-2">
            <StateBadge state={project.state} />
            <span className="text-xs text-muted">{formatDate(project.created_at)}</span>
          </div>
        </div>
      </Link>
      {canDelete ? (
        <button
          type="button"
          disabled={deleting}
          onClick={() => {
            if (!window.confirm(`Delete "${project.title}" and all its files?`)) return;
            setDeleting(true);
            void onDelete(project.id).finally(() => setDeleting(false));
          }}
          aria-label={`Delete ${project.title}`}
          className="absolute top-2.5 right-2.5 grid size-9 place-items-center rounded-full bg-white/90 text-danger shadow-sm transition-colors hover:bg-danger hover:text-white disabled:opacity-50"
        >
          <Trash2 className="size-4" aria-hidden />
        </button>
      ) : null}
    </div>
  );
}
