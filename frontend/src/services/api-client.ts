/**
 * Typed HTTP client for the ClipMaker backend.
 *
 * - Attaches the current user's bearer token (from the auth provider's token getter).
 * - Converts every non-2xx response into an `ApiError` carrying the backend's stable `code`.
 * - Never retries mutations silently; callers decide how to surface failures.
 */
import { env } from "@/lib/env";

/** Error raised for any failed API call. `code` mirrors backend error codes. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/** Returns a fresh access token, or null when signed out. */
export type TokenGetter = () => Promise<string | null>;

let getToken: TokenGetter = async () => null;

/** Called once by the AuthProvider so services can authenticate requests. */
export function setTokenGetter(getter: TokenGetter): void {
  getToken = getter;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  /** Skip the Authorization header (public endpoints). */
  anonymous?: boolean;
  signal?: AbortSignal;
}

function isErrorBody(value: unknown): value is { code: string; message: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).code === "string" &&
    typeof (value as Record<string, unknown>).message === "string"
  );
}

/** Perform a JSON request against the backend and return the parsed body. */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (!options.anonymous) {
    const token = await getToken();
    if (!token) throw new ApiError(401, "unauthorized", "Please sign in again.");
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${env.apiUrl}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(0, "network_error", "Can't reach the server. Check your connection.");
  }

  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (isErrorBody(payload)) throw new ApiError(response.status, payload.code, payload.message);
    throw new ApiError(response.status, "http_error", `Request failed (${response.status}).`);
  }
  return payload as T;
}
