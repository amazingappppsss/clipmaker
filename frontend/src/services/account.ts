/** Account endpoints (backend/src/clipmaker/api/account.py). */
import { apiRequest } from "@/services/api-client";
import type { AccountUsage, DevToken, PlanInfo } from "@/services/api-types";

export function getUsage(): Promise<AccountUsage> {
  return apiRequest<AccountUsage>("/account/usage");
}

/** Development-only login; the backend refuses this route in production. */
export function fetchDevToken(email: string): Promise<DevToken> {
  return apiRequest<DevToken>("/dev/token", { method: "POST", body: { email }, anonymous: true });
}

/** Public plan catalog (no sign-in required). */
export function listPlans(): Promise<PlanInfo[]> {
  return apiRequest<PlanInfo[]>("/plans", { anonymous: true });
}
