import path from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for the Docker image (frontend/Dockerfile).
  output: "standalone",
  // Monorepo: trace files from the repository root (shared /common types).
  outputFileTracingRoot: path.join(__dirname, ".."),
  // The dev/preview /api proxy buffers request bodies (default cap 10 MB), which would cut off
  // video uploads to local storage. Raise it only when that proxy is on; production uploads go
  // straight to R2 and never pass through Next.js.
  ...(process.env.API_PROXY_TARGET
    ? { experimental: { proxyClientMaxBodySize: "2gb" as const } }
    : {}),
  cacheComponents: true,
  partialPrefetching: true,
  // Dev/preview convenience: when API_PROXY_TARGET is set (e.g. http://localhost:8000), the web
  // server forwards /api/* to the backend so a single port serves everything. Unset in
  // production, where the frontend calls the API's own domain via NEXT_PUBLIC_API_URL.
  // Browser hardening. Next.js ships none of these by default, so the page could be framed
  // for clickjacking and its referrer leaked to anything it links to.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
        ],
      },
    ];
  },
  async rewrites() {
    const target = process.env.API_PROXY_TARGET;
    return target ? [{ source: "/api/:path*", destination: `${target.replace(/\/$/, "")}/:path*` }] : [];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
