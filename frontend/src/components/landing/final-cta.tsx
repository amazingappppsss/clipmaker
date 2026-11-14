"use client";

/** The one-step input again at the bottom of the page, so nobody has to scroll back up. */
import { useState } from "react";

import { LinkBar } from "@/components/upload/link-bar";
import { Alert } from "@/components/ui/alert";

export function CtaLinkBar() {
  const [error, setError] = useState<string | null>(null);
  return (
    <div className="mx-auto mt-10 max-w-xl text-left">
      <LinkBar onError={setError} />
      {error ? (
        <div className="mt-4">
          <Alert tone="error">{error}</Alert>
        </div>
      ) : null}
    </div>
  );
}
