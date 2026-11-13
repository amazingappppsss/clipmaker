/** Dashboard grid card for one project. */
import { Film } from "lucide-react";
import Link from "next/link";

import { StateBadge } from "@/components/app/state-badge";
import { formatDate, formatDuration } from "@/lib/format";
import type { Project } from "@/services/api-types";

export function ProjectCard({ project }: { project: Project }) {
  const duration = project.source_video?.duration_seconds;
  return (
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
  );
}
