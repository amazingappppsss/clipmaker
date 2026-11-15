/** Pre-launch waitlist endpoints (backend/src/clipmaker/api/waitlist.py). Public: no token. */
import { apiRequest } from "@/services/api-client";
import type { WaitlistPlace, WaitlistStats } from "@/services/api-types";

export function getWaitlistStats(): Promise<WaitlistStats> {
  return apiRequest<WaitlistStats>("/waitlist/stats", { anonymous: true });
}

export function joinWaitlist(input: {
  email: string;
  source?: string;
  referral_code?: string;
  /** Hidden field: a real person leaves it empty. */
  company: string;
}): Promise<WaitlistPlace> {
  return apiRequest<WaitlistPlace>("/waitlist", {
    method: "POST",
    body: input,
    anonymous: true,
  });
}
