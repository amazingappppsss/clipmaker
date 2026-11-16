/** Project endpoints (backend/src/clipmaker/api/projects.py). */
import { env } from "@/lib/env";
import { apiRequest } from "@/services/api-client";
import type {
  Clip,
  Moments,
  ImportRequest,
  JobStatus,
  Project,
  ProjectCreate,
  ProjectList,
  UploadRequest,
  UploadTicket,
} from "@/services/api-types";

export function createProject(body: ProjectCreate): Promise<Project> {
  return apiRequest<Project>("/projects", { method: "POST", body });
}

export function listProjects(cursor?: string | null, limit = 20): Promise<ProjectList> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return apiRequest<ProjectList>(`/projects?${params.toString()}`);
}

export function getProject(id: string, signal?: AbortSignal): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(id)}`, { signal });
}

export function deleteProject(id: string): Promise<void> {
  return apiRequest<void>(`/projects/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function requestUpload(id: string, body: UploadRequest): Promise<UploadTicket> {
  return apiRequest<UploadTicket>(`/projects/${encodeURIComponent(id)}/upload`, {
    method: "POST",
    body,
  });
}

export function completeUpload(id: string): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(id)}/upload/complete`, {
    method: "POST",
  });
}

/** Charge credits and start (or retry) background processing. */
export function startProcessing(id: string): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(id)}/process`, { method: "POST" });
}

export function getStatus(id: string, signal?: AbortSignal): Promise<JobStatus> {
  return apiRequest<JobStatus>(`/projects/${encodeURIComponent(id)}/status`, { signal });
}

export function getClips(id: string, signal?: AbortSignal): Promise<Clip[]> {
  return apiRequest<Clip[]>(`/projects/${encodeURIComponent(id)}/clips`, { signal });
}

/** Create a project from a video link (e.g. YouTube); the download runs in the background. */
export function importFromUrl(body: ImportRequest): Promise<Project> {
  return apiRequest<Project>("/projects/import", { method: "POST", body });
}

/** Read-only link to this project's picked moments (JSON, no video files). */
export async function shareProject(id: string): Promise<string> {
  const { token } = await apiRequest<{ token: string }>(
    `/projects/${encodeURIComponent(id)}/share`,
    { method: "POST" },
  );
  return `${env.apiUrl}/share/${encodeURIComponent(token)}`;
}

/** Stop processing; credits for the run are refunded. */
export function cancelProcessing(id: string): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(id)}/cancel`, { method: "POST" });
}

/** Correct a clip the AI got wrong and rebuild just that one (not charged). */
export function correctClip(
  projectId: string,
  clipId: string,
  changes: { start_seconds?: number; end_seconds?: number },
): Promise<{ status: string }> {
  return apiRequest<{ status: string }>(`/projects/${projectId}/clips/${clipId}`, {
    method: "PATCH",
    body: changes,
  });
}

/** Every moment we scored for this project, shipped or not. */
export function getMoments(projectId: string, signal?: AbortSignal): Promise<Moments> {
  return apiRequest<Moments>(`/projects/${projectId}/moments`, { signal });
}

/** Turn a moment we rejected into a real clip (not charged). */
export function promoteMoment(projectId: string, momentId: string): Promise<{ status: string }> {
  return apiRequest<{ status: string }>(`/projects/${projectId}/moments/${momentId}/promote`, {
    method: "POST",
  });
}
