"use client";

/**
 * Link tab of New Project: paste a YouTube link → confirm rights → (optional) settings →
 * "Get clips" imports the link and starts processing in one step.
 * The download itself happens in the background worker, so this returns in seconds.
 */
import { Link2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { DEFAULT_SETTINGS, SettingsBar } from "@/components/upload/settings-bar";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { looksLikeYouTubeUrl } from "@/lib/youtube";
import { ApiError } from "@/services/api-client";
import type { ProjectSettings } from "@/services/api-types";
import { importFromUrl, startProcessing } from "@/services/projects";

export function LinkFlow({ initialUrl = "" }: { initialUrl?: string }) {
  const router = useRouter();
  const [url, setUrl] = useState(initialUrl);
  const [rights, setRights] = useState(false);
  const [settings, setSettings] = useState<Required<ProjectSettings>>(DEFAULT_SETTINGS);
  const [busy, setBusy] = useState<"checking" | "starting" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setError(null);
    if (!looksLikeYouTubeUrl(url)) {
      setError("Paste a YouTube link (youtube.com or youtu.be).");
      return;
    }
    if (!rights) {
      setError("Please confirm you own this video or have permission to use it.");
      return;
    }
    setBusy("checking");
    try {
      const project = await importFromUrl({ url: url.trim(), rights_confirmed: true, settings });
      setBusy("starting");
      try {
        await startProcessing(project.id);
      } finally {
        // Even if starting fails (e.g. not enough credits) the project page explains why.
        router.push(`/projects/${project.id}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setBusy(null);
    }
  };

  return (
    <form onSubmit={(e) => void submit(e)} className="mx-auto flex w-full max-w-2xl flex-col gap-5">
      <label className="flex items-center gap-3 rounded-full border-2 border-ink bg-white p-2 pl-5 shadow-[6px_6px_0_0_var(--color-ink)]">
        <Link2 className="size-5 shrink-0 text-blue" aria-hidden />
        <span className="sr-only">YouTube link</span>
        <input
          type="url"
          inputMode="url"
          autoComplete="off"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste a YouTube link…"
          className="min-w-0 flex-1 bg-transparent py-2 font-semibold outline-none placeholder:font-normal placeholder:text-muted"
        />
      </label>

      <label className="flex items-start gap-3 text-sm text-ink-soft">
        <input
          type="checkbox"
          checked={rights}
          onChange={(e) => setRights(e.target.checked)}
          className="mt-0.5 size-4 accent-[var(--color-blue)]"
        />
        I own this video or have permission to use it.
      </label>

      <SettingsBar value={settings} onChange={setSettings} disabled={busy !== null} />

      {error ? <Alert tone="error">{error}</Alert> : null}

      <div className="flex justify-center">
        <Button type="submit" size="lg" className="uppercase" loading={busy !== null}>
          {busy === "checking" ? "Checking link…" : busy === "starting" ? "Starting…" : "Get clips"}
        </Button>
      </div>
    </form>
  );
}
