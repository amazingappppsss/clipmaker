"use client";

/** Dashboard: the user's projects, newest first, with "load more" pagination. */
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ProjectCard } from "@/components/app/project-card";
import { VideoDropZone } from "@/components/upload/video-drop-zone";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { setPendingUpload } from "@/lib/pending-upload";
import { ApiError } from "@/services/api-client";
import type { Project } from "@/services/api-types";
import { listProjects } from "@/services/projects";

export function ProjectList() {
  const router = useRouter();
  const [items, setItems] = useState<Project[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (after: string | null): Promise<void> => {
    try {
      const page = await listProjects(after);
      setItems((prev) => (after && prev ? [...prev, ...page.items] : page.items));
      setCursor(page.next_cursor ?? null);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load your projects.");
      setItems((prev) => prev ?? []);
    }
  }, []);

  useEffect(() => {
    // State is set only after the request resolves (external-system sync), not synchronously.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(null);
  }, [load]);

  const loadMore = async (): Promise<void> => {
    setLoadingMore(true);
    await load(cursor);
    setLoadingMore(false);
  };

  return (
    <div>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="display-heavy text-4xl">Projects</h1>
          <p className="mt-1 text-muted">Every video you upload and the clips made from it.</p>
        </div>
        {items && items.length > 0 ? <ButtonLink href="/new">New project</ButtonLink> : null}
      </div>

      {error ? (
        <div className="mt-6">
          <Alert tone="error">{error}</Alert>
        </div>
      ) : null}

      {items === null ? (
        <div className="mt-20 flex justify-center text-muted">
          <Spinner />
        </div>
      ) : items.length === 0 ? (
        <div className="mx-auto mt-12 max-w-2xl">
          <p className="mb-4 text-center font-medium">Start with your first video</p>
          <VideoDropZone
            onFile={(file) => {
              setPendingUpload(file);
              router.push("/new");
            }}
            onReject={setError}
          />
        </div>
      ) : (
        <>
          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
          {cursor ? (
            <div className="mt-8 flex justify-center">
              <Button variant="secondary" onClick={() => void loadMore()} loading={loadingMore}>
                Load more
              </Button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
