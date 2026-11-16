/**
 * Friendly aliases for the generated API contract.
 * Source of truth: backend Pydantic models → `npm run gen:types` → common/types/api.ts.
 * Never hand-write API shapes elsewhere in the frontend; import them from here.
 */
import type { components } from "@common/types/api";

type Schemas = components["schemas"];

export type Project = Schemas["ProjectOut"];
export type ProjectList = Schemas["ProjectList"];
export type ProjectCreate = Schemas["ProjectCreate"];
export type ProjectSettings = Schemas["ProjectSettings"];
export type ProjectState = Schemas["ProjectState"];
export type SourceVideo = Schemas["SourceVideoOut"];
export type UploadRequest = Schemas["UploadRequest"];
export type UploadTicket = Schemas["UploadTicket"];
export type AccountUsage = Schemas["AccountUsage"];
export type UsageRecord = Schemas["UsageRecordOut"];
export type PlanInfo = Schemas["PlanOut"];
export type ContentCategory = Schemas["ContentCategory"];
export type VideoStyle = Schemas["VideoStyle"];
export type DevToken = Schemas["DevTokenOut"];
export type ClipCount = NonNullable<ProjectSettings["clip_count"]>;
export type Clip = Schemas["ClipOut"];
export type JobStatus = Schemas["JobStatusOut"];
export type StageStatus = Schemas["StageStatusOut"];
export type ImportRequest = Schemas["ImportRequest"];

/** A person's own spot on the pre-launch waitlist (backend/src/clipmaker/api/waitlist.py). */
export interface WaitlistPlace {
  position: number;
  referral_code: string;
  referrals: number;
  total: number;
  places_per_referral: number;
}

/** Public counters for the pre-launch page. */
export interface WaitlistStats {
  total: number;
  founding_spots: number;
  spots_left: number;
  places_per_referral: number;
}

/** One scored moment, shipped or not (backend/src/clipmaker/services/moments.py). */
export interface Moment {
  id: string;
  start_seconds: number;
  end_seconds: number;
  score: number;
  selected: boolean;
  rejected_reason: string | null;
  why: string;
  hook_type: string | null;
  transcript: string | null;
  can_promote: boolean;
}

/** Every moment we looked at, with the headline counts. */
export interface Moments {
  scanned: number;
  shipped: number;
  moments: Moment[];
}
