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
          "group flex w-full cursor-pointer items-center gap-3 rounded-full border-2 border-ink bg-white p-2 pl-5 text-left",
          "shadow-[6px_6px_0_0_var(--color-ink)] transition-all duration-200 sm:gap-4",
          dragging
            ? "scale-[1.02] bg-lime"
            : "hover:-translate-y-0.5 hover:shadow-[8px_8px_0_0_var(--color-ink)]",
          disabled ? "cursor-not-allowed opacity-60" : "",
        ].join(" ")}
      >
        <UploadCloud className="size-5 shrink-0 text-blue" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="block truncate font-semibold text-ink">
            {dragging ? "Drop it" : "Drop a video or click to upload"}
          </span>
          <span id={hintId} className="hidden truncate text-xs text-muted sm:block">
            {HINT}
          </span>
        </span>
        <span className="inline-flex h-12 shrink-0 items-center gap-1.5 rounded-full border-2 border-ink bg-lime px-5 font-display text-sm font-black tracking-wide text-ink uppercase transition-transform group-hover:rotate-[-2deg] sm:px-6">
          Get clips
          <ArrowRight className="size-4" aria-hidden />
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
        "border-2 border-dashed bg-surface px-6 py-14 text-center transition-all duration-200",
        dragging
          ? "scale-[1.01] border-blue bg-blue-soft"
          : "border-line-strong hover:border-blue/60",
        disabled ? "cursor-not-allowed opacity-60" : "",
      ].join(" ")}
    >
      <span className="grid size-16 -rotate-6 place-items-center rounded-2xl border-2 border-ink bg-lime text-ink shadow-[4px_4px_0_0_var(--color-ink)] transition-transform group-hover:rotate-0">
        <UploadCloud className="size-7" aria-hidden />
      </span>
      <div>
        <p className="display-heavy text-2xl">{dragging ? "Drop it!" : "Drop your video here"}</p>
        <p className="mt-1 text-muted">
          or{" "}
          <span className="font-semibold text-blue underline underline-offset-4">browse files</span>
        </p>
      </div>
      <p id={hintId} className="text-xs text-muted">
        {HINT} · podcasts and talking-head videos work best
      </p>
      {input}
    </div>
  );
}
