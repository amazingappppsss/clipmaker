"use client";

/**
 * Upload tab of New Project: choose a file → (optional) tweak settings → upload with real byte
 * progress → server-side verification → open the project page.
 */
import { Film, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { DEFAULT_SETTINGS, SettingsBar } from "@/components/upload/settings-bar";
import { VideoDropZone } from "@/components/upload/video-drop-zone";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { formatBytes } from "@/lib/format";
import { takePendingUpload } from "@/lib/pending-upload";
import { ApiError } from "@/services/api-client";
import type { ProjectSettings } from "@/services/api-types";
import { uploadNewProject, type UploadProgress } from "@/services/upload";

const PHASE_LABEL: Record<UploadProgress["phase"], string> = {
  creating: "Creating project…",
  uploading: "Uploading",
  verifying: "Checking your video…",
  done: "Done",
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof DOMException && error.name === "AbortError") return "Upload cancelled.";
  return "Something went wrong. Please try again.";
}

export function UploadFlow() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [settings, setSettings] = useState<Required<ProjectSettings>>(DEFAULT_SETTINGS);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // A file dropped on the landing page before signing in continues here.
  useEffect(() => {
    const pending = takePendingUpload();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time handoff from module state
    if (pending) setFile(pending);
  }, []);

  // Warn before leaving mid-upload; the upload would be lost.
  useEffect(() => {
    if (!progress || progress.phase === "done") return undefined;
    const handler = (e: BeforeUnloadEvent): void => e.preventDefault();
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [progress]);

  const busy = progress !== null && progress.phase !== "done";

  const start = async (): Promise<void> => {
    if (!file) return;
    setError(null);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const project = await uploadNewProject(file, settings, setProgress, controller.signal);
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setProgress(null);
    } finally {
      abortRef.current = null;
    }
  };

  const percent =
    progress && progress.total > 0 ? Math.round((progress.loaded / progress.total) * 100) : 0;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-5">
      {!file ? (
        <VideoDropZone onFile={(f) => (setError(null), setFile(f))} onReject={setError} />
      ) : (
        <div className="rounded-[var(--radius-card)] border border-line bg-surface p-5 shadow-[var(--shadow-card)]">
          <div className="flex items-center gap-4">
            <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-sunken">
              <Film className="size-5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{file.name}</p>
              <p className="text-sm text-muted">{formatBytes(file.size)}</p>
            </div>
            {busy ? (
              <Button variant="ghost" size="sm" onClick={() => abortRef.current?.abort()}>
                Cancel
              </Button>
            ) : (
              <button
                type="button"
                aria-label="Remove file"
                className="grid size-8 place-items-center rounded-full text-muted hover:bg-sunken hover:text-ink"
                onClick={() => setFile(null)}
              >
                <X className="size-4" />
              </button>
            )}
          </div>

          {progress ? (
            <div className="mt-5" aria-live="polite">
              <div className="mb-2 flex justify-between text-sm">
                <span className="font-medium">{PHASE_LABEL[progress.phase]}</span>
                {progress.phase === "uploading" ? (
                  <span className="tabular-nums text-muted">
                    {formatBytes(progress.loaded)} of {formatBytes(progress.total)} · {percent}%
                  </span>
                ) : null}
              </div>
              <div
                className="h-2 overflow-hidden rounded-full bg-sunken"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progress.phase === "uploading" ? percent : undefined}
              >
                <div
                  className={`h-full rounded-full bg-blue transition-[width] duration-300 ${
                    progress.phase === "uploading" ? "" : "w-full animate-pulse"
                  }`}
                  style={progress.phase === "uploading" ? { width: `${percent}%` } : undefined}
                />
              </div>
            </div>
          ) : null}
        </div>
      )}

      <SettingsBar value={settings} onChange={setSettings} disabled={busy} />

      {error ? <Alert tone="error">{error}</Alert> : null}

      {file ? (
        <div className="flex justify-center">
          <Button size="lg" onClick={() => void start()} loading={busy} disabled={busy}>
            {busy ? "Uploading…" : "Upload video"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
