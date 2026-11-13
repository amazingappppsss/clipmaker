"use client";

/**
 * Landing hero input (Opus Clip style): paste a YouTube link → GET CLIPS, or upload a file.
 * Both hand off to /new (through sign-in when needed): the link via localStorage (survives the
 * magic-link redirect), the file in memory.
 */
import { ArrowRight, Link2, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";

import { useAuth } from "@/lib/auth/auth-provider";
import { setPendingLink, setPendingUpload } from "@/lib/pending-upload";
import { looksLikeYouTubeUrl } from "@/lib/youtube";
import { ACCEPTED_VIDEO_TYPES, resolveContentType } from "@/services/upload";

const ACCEPT_ATTR = [
  ...Object.keys(ACCEPTED_VIDEO_TYPES),
  ...Object.values(ACCEPTED_VIDEO_TYPES),
].join(",");

export function LinkBar({ onError }: { onError: (message: string | null) => void }) {
  const router = useRouter();
  const { status } = useAuth();
  const [url, setUrl] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const next = status === "signed_in" ? "/new" : "/login?next=/new";

  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (!looksLikeYouTubeUrl(url)) {
      onError("Paste a YouTube link (youtube.com or youtu.be), or upload a file.");
      return;
    }
    onError(null);
    setPendingLink(url.trim());
    router.push(next);
  };

  const onFile = (file: File | undefined): void => {
    if (!file) return;
    if (!resolveContentType(file)) {
      onError("That file type isn't supported. Upload an MP4, MOV, WebM or MKV video.");
      return;
    }
    onError(null);
    setPendingUpload(file);
    router.push(next);
  };

  return (
    <div>
      <form
        onSubmit={submit}
        className="flex w-full items-center gap-2 rounded-full border-2 border-ink bg-white p-2 pl-5 shadow-[6px_6px_0_0_var(--color-ink)] sm:gap-3"
      >
        <Link2 className="size-5 shrink-0 text-blue" aria-hidden />
        <label className="sr-only" htmlFor="hero-link">
          YouTube link
        </label>
        <input
          id="hero-link"
          type="url"
          inputMode="url"
          autoComplete="off"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste a YouTube link…"
          className="min-w-0 flex-1 bg-transparent py-2 font-semibold text-ink outline-none placeholder:font-normal placeholder:text-muted"
        />
        <button
          type="submit"
          className="inline-flex h-12 shrink-0 items-center gap-1.5 rounded-full border-2 border-ink bg-lime px-5 font-display text-sm font-black tracking-wide text-ink uppercase transition-transform hover:-rotate-2 sm:px-6"
        >
          Get clips <ArrowRight className="size-4" aria-hidden />
        </button>
      </form>
      <div className="mt-4 flex justify-center">
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold text-white/90 underline-offset-4 hover:underline"
        >
          <UploadCloud className="size-4" aria-hidden /> or upload a video file
        </button>
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT_ATTR}
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          onChange={(e) => {
            onFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </div>
    </div>
  );
}
