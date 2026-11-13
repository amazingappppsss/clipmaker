/** Project endpoints (backend/src/clipmaker/api/projects.py). */
import { apiRequest } from "@/services/api-client";
import type {
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
