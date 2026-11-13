/** Signed-in area. Suspense is required because the shell reads the URL (Next 16 rules). */
import { Suspense, type ReactNode } from "react";

import { AppShell } from "@/components/app/app-shell";
import { Spinner } from "@/components/ui/spinner";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="grid min-h-dvh place-items-center text-muted">
          <Spinner />
        </div>
      }
    >
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
