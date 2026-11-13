// Vitest config. Tests live in /tests/frontend (repo convention: tests outside source dirs).
import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@common": path.resolve(__dirname, "../common"),
    },
  },
  test: {
    root: path.resolve(__dirname, ".."),
    include: ["tests/frontend/**/*.test.{ts,tsx}"],
    environment: "jsdom",
    setupFiles: [path.resolve(__dirname, "../tests/frontend/setup.ts")],
  },
});
