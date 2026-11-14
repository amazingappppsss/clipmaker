/** Pure formatting helpers (unit-tested in tests/frontend/format.test.ts). */

/** 1536 → "1.5 KB". */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  return `${value.toFixed(digits)} ${units[unit]}`;
}

/** 3725 → "1:02:05", 65 → "1:05". */
export function formatDuration(totalSeconds: number | null | undefined): string {
  if (totalSeconds == null || !Number.isFinite(totalSeconds) || totalSeconds < 0) return "—";
  const s = Math.round(totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

/** ISO timestamp → "13 Nov 2026". */
export function formatDate(iso: string, locale = "en-GB"): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(locale, { day: "numeric", month: "short", year: "numeric" });
}

/** 1500 (cents) → "$15", 1499 → "$14.99", 0 → "Free". */
export function formatUsd(cents: number): string {
  if (cents === 0) return "Free";
  const dollars = cents / 100;
  return `$${Number.isInteger(dollars) ? dollars.toLocaleString("en-US") : dollars.toFixed(2)}`;
}

const HOOK_LABELS: Record<string, string> = {
  question: "Question hook",
  hypothetical: "“What if…” hook",
  bold_claim: "Bold claim",
  shocking_number: "Shocking number",
  quote_rebuttal: "Quote → pushback",
  confession: "Confession",
  famous_name: "Famous name",
  story_in_motion: "Mid-story start",
  secret_reveal: "Secret reveal",
  warning: "Warning",
  call_out: "Calls out the viewer",
  result_first: "Result first",
  emotional: "Raw emotion",
  funny: "Funny",
};

/** Creator-facing name for a hook type (null when unknown or "none"). */
export function hookLabel(type: string | null | undefined): string | null {
  return type ? (HOOK_LABELS[type] ?? null) : null;
}
