import "@fontsource-variable/inter";
import "@fontsource-variable/bricolage-grotesque";
import "./globals.css";

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/lib/auth/auth-provider";

export const metadata: Metadata = {
  title: { default: "ClipMaker — Paste a video. Get finished shorts.", template: "%s · ClipMaker" },
  description:
    "ClipMaker turns long videos and podcasts into ready-to-post vertical shorts with captions, hooks and speaker-aware framing.",
};

export const viewport: Viewport = { themeColor: "#ff3d8b" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
