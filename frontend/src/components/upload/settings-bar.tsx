"use client";

/**
 * Project settings as compact chips (PRD §4 step 2). Every option defaults to "Auto",
 * so users can ignore this entirely. Native <select>s keep it accessible on every device.
 */
import { ChevronDown } from "lucide-react";
import type { ChangeEvent } from "react";

import type { ClipCount, ContentCategory, ProjectSettings, VideoStyle } from "@/services/api-types";

export const DEFAULT_SETTINGS: Required<ProjectSettings> = {
  category: "auto",
  language: "auto",
  clip_count: "auto",
  style: "auto",
};

interface Option<T extends string> {
  value: T;
  label: string;
}

const CATEGORIES: Option<ContentCategory>[] = [
  { value: "auto", label: "Auto-detect" },
  { value: "podcast", label: "Podcast" },
  { value: "interview", label: "Interview" },
  { value: "educational", label: "Educational" },
  { value: "business", label: "Business" },
  { value: "gaming", label: "Gaming" },
];

const LANGUAGES: Option<string>[] = [
  { value: "auto", label: "Auto-detect" },
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi" },
  { value: "es", label: "Spanish" },
  { value: "pt", label: "Portuguese" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "ar", label: "Arabic" },
  { value: "ja", label: "Japanese" },
];

const CLIP_COUNTS: Option<string>[] = [
  { value: "auto", label: "Auto" },
  { value: "3", label: "3 clips" },
  { value: "5", label: "5 clips" },
  { value: "10", label: "10 clips" },
];

const STYLES: Option<VideoStyle>[] = [
  { value: "auto", label: "Auto" },
  { value: "modern_creator", label: "Modern Creator" },
  { value: "minimal_professional", label: "Minimal Pro" },
];

function parseClipCount(value: string): ClipCount {
  return value === "auto" ? "auto" : (Number(value) as 3 | 5 | 10);
}

interface ChipProps<T extends string> {
  label: string;
  value: T;
  options: Option<T>[];
  disabled?: boolean;
  onChange: (value: T) => void;
}

function Chip<T extends string>({ label, value, options, disabled, onChange }: ChipProps<T>) {
  const current = options.find((o) => o.value === value)?.label ?? value;
  return (
    <label className="relative inline-flex h-9 items-center gap-1.5 rounded-full border border-line bg-surface pr-3 pl-3.5 text-sm transition-colors focus-within:border-ink/50 hover:border-line-strong">
      <span className="text-muted">{label}</span>
      <span className="font-medium">{current}</span>
      <ChevronDown className="size-3.5 text-muted" aria-hidden />
      <select
        aria-label={label}
        className="absolute inset-0 cursor-pointer opacity-0 disabled:cursor-not-allowed"
        value={value}
        disabled={disabled}
        onChange={(e: ChangeEvent<HTMLSelectElement>) => onChange(e.target.value as T)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

interface SettingsBarProps {
  value: Required<ProjectSettings>;
  onChange: (value: Required<ProjectSettings>) => void;
  disabled?: boolean;
}

export function SettingsBar({ value, onChange, disabled }: SettingsBarProps) {
  return (
    <div
      className="flex flex-wrap items-center justify-center gap-2"
      role="group"
      aria-label="Project settings"
    >
      <Chip
        label="Type"
        value={value.category}
        options={CATEGORIES}
        disabled={disabled}
        onChange={(category) => onChange({ ...value, category })}
      />
      <Chip
        label="Language"
        value={value.language}
        options={LANGUAGES}
        disabled={disabled}
        onChange={(language) => onChange({ ...value, language })}
      />
      <Chip
        label="Clips"
        value={String(value.clip_count)}
        options={CLIP_COUNTS}
        disabled={disabled}
        onChange={(count) => onChange({ ...value, clip_count: parseClipCount(count) })}
      />
      <Chip
        label="Style"
        value={value.style}
        options={STYLES}
        disabled={disabled}
        onChange={(style) => onChange({ ...value, style })}
      />
    </div>
  );
}
