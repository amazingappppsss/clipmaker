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
      className="group overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface transition-shadow hover:shadow-[var(--shadow-card)]"
    >
      <div className="relative aspect-video bg-sunken">
        {project.thumbnail_url ? (
          // Signed storage URLs are short-lived and external, so next/image optimisation does not apply.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={project.thumbnail_url} alt="" className="size-full object-cover" />
        ) : (
          <div className="grid size-full place-items-center text-muted">
            <Film className="size-6" aria-hidden />
          </div>
        )}
        {duration ? (
          <span className="absolute right-2.5 bottom-2.5 rounded-md bg-ink/80 px-1.5 py-0.5 text-xs font-medium text-white tabular-nums">
            {formatDuration(duration)}
          </span>
        ) : null}
      </div>
      <div className="p-4">
        <p className="truncate font-medium group-hover:underline group-hover:underline-offset-4">
          {project.title}
        </p>
        <div className="mt-2 flex items-center justify-between gap-2">
          <StateBadge state={project.state} />
          <span className="text-xs text-muted">{formatDate(project.created_at)}</span>
        </div>
      </div>
    </Link>
  );
}
