import "@fontsource-variable/inter";
import "@fontsource-variable/archivo/wdth.css";
import "@fontsource/press-start-2p";
import "./globals.css";

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/lib/auth/auth-provider";

export const metadata: Metadata = {
  title: { default: "Clip2Easy — Paste a video. Get finished shorts.", template: "%s · Clip2Easy" },
  description:
    "Clip2Easy turns long videos and podcasts into ready-to-post vertical shorts with captions, hooks and speaker-aware framing.",
};

export const viewport: Viewport = { themeColor: "#1e3bea" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
