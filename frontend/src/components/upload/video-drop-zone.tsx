"use client";

/**
 * The primary input of the product: one drop target, two looks.
 * - "bar":   chunky prompt-style input for the landing hero.
 * - "panel": large dashed area for the New Project page and empty dashboard.
 * Same behavior everywhere so users learn one interaction.
 */
import { ArrowRight, UploadCloud } from "lucide-react";
import { useId, useRef, useState, type DragEvent, type KeyboardEvent } from "react";

import { ACCEPTED_VIDEO_TYPES, resolveContentType } from "@/services/upload";

interface VideoDropZoneProps {
  onFile: (file: File) => void;
  onReject?: (message: string) => void;
  disabled?: boolean;
  variant?: "bar" | "panel";
}

const ACCEPT_ATTR = [
  ...Object.keys(ACCEPTED_VIDEO_TYPES),
  ...Object.values(ACCEPTED_VIDEO_TYPES),
].join(",");

const HINT = "MP4, MOV, WebM or MKV · up to 4 hours";

export function VideoDropZone({
  onFile,
  onReject,
  disabled = false,
  variant = "panel",
}: VideoDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const hintId = useId();
  const [dragging, setDragging] = useState(false);

  const accept = (file: File | undefined): void => {
    if (!file) return;
    if (!resolveContentType(file)) {
      onReject?.("That file type isn't supported. Upload an MP4, MOV, WebM or MKV video.");
      return;
    }
    onFile(file);
  };

  const onDrop = (event: DragEvent<HTMLDivElement>): void => {
    event.preventDefault();
    setDragging(false);
    if (!disabled) accept(event.dataTransfer.files[0]);
  };

  const openPicker = (): void => {
    if (!disabled) inputRef.current?.click();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openPicker();
    }
  };

  const shared = {
    role: "button" as const,
    tabIndex: disabled ? -1 : 0,
    "aria-disabled": disabled,
    "aria-describedby": hintId,
    onClick: openPicker,
    onKeyDown,
    onDragOver: (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (!disabled) setDragging(true);
    },
    onDragLeave: () => setDragging(false),
    onDrop,
  };

  const input = (
    <input
      ref={inputRef}
      type="file"
      accept={ACCEPT_ATTR}
      className="sr-only"
      tabIndex={-1}
      aria-hidden
      onChange={(e) => {
        accept(e.target.files?.[0]);
        e.target.value = "";
      }}
    />
  );

  if (variant === "bar") {
    return (
      <div
        {...shared}
        className={[
          "group flex w-full cursor-pointer items-center gap-4 rounded-[1.75rem] bg-white p-3 pl-4 text-left",
          "shadow-[var(--shadow-float)] ring-4 transition-all duration-200 sm:p-4 sm:pl-5",
          dragging ? "scale-[1.02] ring-sun" : "ring-white/30 hover:ring-white/60",
          disabled ? "cursor-not-allowed opacity-60" : "",
        ].join(" ")}
      >
        <span className="gradient-fill grid size-12 shrink-0 place-items-center rounded-2xl text-white sm:size-14">
          <UploadCloud className="size-6" aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-display text-lg font-bold text-ink sm:text-xl">
            {dragging ? "Drop it!" : "Drop your video here"}
          </span>
          <span id={hintId} className="block truncate text-sm text-muted">
            or click to browse · {HINT}
          </span>
        </span>
        <span className="grid size-12 shrink-0 place-items-center rounded-full bg-ink text-white transition-transform group-hover:translate-x-0.5 sm:size-14">
          <ArrowRight className="size-5" aria-hidden />
        </span>
        {input}
      </div>
    );
  }

  return (
    <div
      {...shared}
      className={[
        "group flex w-full cursor-pointer flex-col items-center justify-center gap-4 rounded-[var(--radius-card)]",
        "border-[3px] border-dashed bg-surface px-6 py-14 text-center transition-all duration-200",
        dragging
          ? "scale-[1.01] border-magenta bg-info-soft"
          : "border-line-strong hover:border-magenta/60",
        disabled ? "cursor-not-allowed opacity-60" : "",
      ].join(" ")}
    >
      <span className="gradient-fill grid size-16 -rotate-6 place-items-center rounded-3xl text-white shadow-[var(--shadow-glow)] transition-transform group-hover:rotate-0">
        <UploadCloud className="size-7" aria-hidden />
      </span>
      <div>
        <p className="font-display text-2xl font-bold">
          {dragging ? "Drop it!" : "Drop your video here"}
        </p>
        <p className="mt-1 text-muted">
          or{" "}
          <span className="font-semibold text-magenta underline underline-offset-4">
            browse files
          </span>
        </p>
      </div>
      <p id={hintId} className="text-xs text-muted">
        {HINT} · podcasts and talking-head videos work best
      </p>
      {input}
    </div>
  );
}
