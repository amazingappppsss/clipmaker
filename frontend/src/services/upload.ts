/**
 * Source-video upload orchestration:
 *   create project → request signed URL → PUT bytes directly to storage → server verification.
 *
 * Progress is the real number of bytes sent (XHR upload events) — never simulated.
 */
import { ApiError } from "@/services/api-client";
import type { Project, ProjectSettings, UploadTicket } from "@/services/api-types";
import { completeUpload, createProject, requestUpload } from "@/services/projects";

/** Content types the backend accepts (mirrors ALLOWED_VIDEO_TYPES in schemas.py). */
export const ACCEPTED_VIDEO_TYPES: Readonly<Record<string, string>> = {
  "video/mp4": ".mp4",
  "video/quicktime": ".mov",
  "video/webm": ".webm",
  "video/x-matroska": ".mkv",
};

export type UploadPhase = "creating" | "uploading" | "verifying" | "done";

export interface UploadProgress {
  phase: UploadPhase;
  /** Bytes sent so far during the "uploading" phase. */
  loaded: number;
  total: number;
}

/** Some browsers report an empty type for .mkv/.mov; infer it from the extension. */
export function resolveContentType(file: File): string | null {
  if (file.type in ACCEPTED_VIDEO_TYPES) return file.type;
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  const aliases: Record<string, string> = { ".m4v": "video/mp4", ".qt": "video/quicktime" };
  const match = Object.entries(ACCEPTED_VIDEO_TYPES).find(([, e]) => e === ext);
  return match?.[0] ?? aliases[ext] ?? null;
}

/** Derive a readable default project title from a filename. */
export function titleFromFilename(name: string): string {
  const base = name
    .replace(/\.[^.]+$/, "")
    .replace(/[_-]+/g, " ")
    .trim();
  return (base || "Untitled video").slice(0, 200);
}

/** PUT a file to a signed URL, reporting byte progress. Resolves on 2xx. */
export function putFile(
  ticket: UploadTicket,
  file: File,
  onProgress: (loaded: number, total: number) => void,
  signal?: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(ticket.method, ticket.upload_url);
    for (const [name, value] of Object.entries(ticket.headers)) xhr.setRequestHeader(name, value);
    xhr.upload.onprogress = (event: ProgressEvent) => {
      if (event.lengthComputable) onProgress(event.loaded, event.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new ApiError(xhr.status, "upload_failed", "Upload failed. Please try again."));
    };
    xhr.onerror = () =>
      reject(new ApiError(0, "network_error", "Upload interrupted. Check your connection."));
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    signal?.addEventListener("abort", () => xhr.abort(), { once: true });
    xhr.send(file);
  });
}

/**
 * Full upload flow for a new project. Returns the verified project.
 * Throws ApiError with the backend's code (e.g. "no_audio", "too_short") on failure.
 */
export async function uploadNewProject(
  file: File,
  settings: ProjectSettings,
  onProgress: (progress: UploadProgress) => void,
  signal?: AbortSignal,
): Promise<Project> {
  const contentType = resolveContentType(file);
  if (!contentType) {
    throw new ApiError(422, "unsupported_type", "Upload an MP4, MOV, WebM or MKV video.");
  }
  onProgress({ phase: "creating", loaded: 0, total: file.size });
  const project = await createProject({ title: titleFromFilename(file.name), settings });

  const ticket = await requestUpload(project.id, {
    filename: file.name,
    content_type: contentType,
    size_bytes: file.size,
  });
  await putFile(
    ticket,
    file,
    (loaded, total) => onProgress({ phase: "uploading", loaded, total }),
    signal,
  );

  onProgress({ phase: "verifying", loaded: file.size, total: file.size });
  const verified = await completeUpload(project.id);
  onProgress({ phase: "done", loaded: file.size, total: file.size });
  return verified;
}
