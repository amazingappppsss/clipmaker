import "@fontsource-variable/inter";
import "@fontsource/instrument-serif/400.css";
import "@fontsource/instrument-serif/400-italic.css";
import "./globals.css";

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/lib/auth/auth-provider";

export const metadata: Metadata = {
  title: { default: "ClipMaker — Paste a video. Get finished shorts.", template: "%s · ClipMaker" },
  description:
    "ClipMaker turns long videos and podcasts into ready-to-post vertical shorts with captions, hooks and speaker-aware framing.",
};

export const viewport: Viewport = { themeColor: "#fbfaf7" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
