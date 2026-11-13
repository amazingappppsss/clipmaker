"use client";

/** New Project: "Paste link" or "Upload file" tabs. Opens the tab matching any hand-off. */
import { Link2, UploadCloud } from "lucide-react";
import { useEffect, useState } from "react";

import { LinkFlow } from "@/components/upload/link-flow";
import { UploadFlow } from "@/components/upload/upload-flow";
import { hasPendingUpload, takePendingLink } from "@/lib/pending-upload";

type Tab = "link" | "upload";

export function NewProjectFlow() {
  const [tab, setTab] = useState<Tab>("link");
  const [initialUrl, setInitialUrl] = useState<string | null>(null);

  // Hand-offs from the landing page (a pasted link, or a dropped file) pick the tab.
  useEffect(() => {
    const link = takePendingLink();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time handoff from storage
    setInitialUrl(link ?? "");
    if (hasPendingUpload()) setTab("upload");
  }, []);

  const tabClass = (t: Tab): string =>
    `inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold transition-colors ${
      tab === t ? "bg-ink text-white" : "text-muted hover:text-ink"
    }`;

  return (
    <div className="flex flex-col gap-8">
      <div
        role="tablist"
        aria-label="Video source"
        className="mx-auto inline-flex rounded-full bg-surface p-1 ring-1 ring-line"
      >
        <button
          role="tab"
          type="button"
          aria-selected={tab === "link"}
          className={tabClass("link")}
          onClick={() => setTab("link")}
        >
          <Link2 className="size-4" aria-hidden /> Paste link
        </button>
        <button
          role="tab"
          type="button"
          aria-selected={tab === "upload"}
          className={tabClass("upload")}
          onClick={() => setTab("upload")}
        >
          <UploadCloud className="size-4" aria-hidden /> Upload file
        </button>
      </div>
      {tab === "upload" ? (
        <UploadFlow />
      ) : initialUrl !== null ? (
        <LinkFlow key={initialUrl} initialUrl={initialUrl} />
      ) : null}
    </div>
  );
}
