/** Project endpoints (backend/src/clipmaker/api/projects.py). */
import { apiRequest } from "@/services/api-client";
import type {
  Clip,
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
