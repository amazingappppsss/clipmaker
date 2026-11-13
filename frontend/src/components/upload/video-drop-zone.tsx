"use client";

/**
 * The primary input of the product: a single large drop target.
 * Used by the landing hero and the New Project page so users learn one interaction.
 */
import { UploadCloud } from "lucide-react";
import { useId, useRef, useState, type DragEvent, type KeyboardEvent } from "react";

import { ACCEPTED_VIDEO_TYPES, resolveContentType } from "@/services/upload";

interface VideoDropZoneProps {
  onFile: (file: File) => void;
  onReject?: (message: string) => void;
  disabled?: boolean;
  /** Shorter variant for pages where the drop zone is not the hero. */
  compact?: boolean;
}

const ACCEPT_ATTR = [
  ...Object.keys(ACCEPTED_VIDEO_TYPES),
  ...Object.values(ACCEPTED_VIDEO_TYPES),
].join(",");

export function VideoDropZone({
  onFile,
  onReject,
  disabled = false,
  compact = false,
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

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-describedby={hintId}
      onClick={openPicker}
      onKeyDown={onKeyDown}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={[
        "group flex w-full cursor-pointer flex-col items-center justify-center rounded-[var(--radius-card)]",
        "border-2 border-dashed bg-surface text-center transition-all duration-200",
        compact ? "gap-2 px-6 py-8" : "gap-3 px-6 py-12 sm:py-14",
        dragging
          ? "scale-[1.01] border-violet bg-info-soft"
          : "border-line-strong hover:border-ink/40",
        disabled ? "cursor-not-allowed opacity-60" : "",
      ].join(" ")}
    >
      <span
        className={`grid place-items-center rounded-2xl bg-sunken text-ink transition-transform group-hover:-translate-y-0.5 ${
          compact ? "size-11" : "size-14"
        }`}
      >
        <UploadCloud className={compact ? "size-5" : "size-6"} aria-hidden />
      </span>
      <div>
        <p className={`font-medium ${compact ? "text-base" : "text-lg"}`}>
          {dragging ? "Drop to upload" : "Drop your video here"}
        </p>
        <p className="mt-1 text-sm text-muted">
          or <span className="font-medium text-ink underline underline-offset-4">browse files</span>
        </p>
      </div>
      <p id={hintId} className="text-xs text-muted">
        MP4, MOV, WebM or MKV · up to 4 hours · podcasts and talking-head videos work best
      </p>
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
    </div>
  );
}
