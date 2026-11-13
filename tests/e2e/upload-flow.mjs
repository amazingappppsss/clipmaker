// Browser smoke test: landing drop → login → /new (file carried over) → real upload → project page.
// Requires the web app (BASE_URL, default http://localhost:3000) and API running with dev login.
// Usage: node tests/e2e/upload-flow.mjs   (set SCREENSHOT_DIR to save screenshots)
import { execFileSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const { chromium } = createRequire(import.meta.url)("playwright");
const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const SHOTS = process.env.SCREENSHOT_DIR;
const dir = mkdtempSync(path.join(tmpdir(), "clipmaker-e2e-"));
const video = path.join(dir, "podcast-episode.mp4");

execFileSync("ffmpeg", ["-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=40",
  "-f", "lavfi", "-i", "sine=frequency=330:duration=40", "-c:v", "libx264", "-preset", "ultrafast",
  "-c:a", "aac", "-shortest", video]);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("response", (r) => r.status() >= 500 && errors.push(`HTTP ${r.status()} ${r.url()}`));
const shot = async (name) => SHOTS && page.screenshot({ path: path.join(SHOTS, `${name}.png`) });

try {
  await page.goto(BASE, { waitUntil: "networkidle" });
  await shot("landing");
  await page.setInputFiles("input[type=file]", video);
  await page.waitForURL("**/login**");
  await page.fill("input[type=email]", `e2e-${Date.now()}@example.com`);
  await page.click("button[type=submit]");
  await page.waitForURL("**/new");
  await page.getByText("podcast-episode.mp4").waitFor();
  await page.getByRole("button", { name: "Upload video" }).click();
  await page.waitForURL("**/projects/**", { timeout: 60_000 });
  await page.getByText("Ready to find your best moments").waitFor();
  await page.getByRole("button", { name: "Find my clips" }).waitFor();
  await page.getByText("1280×720").waitFor();
  await shot("project");
  if (errors.length) throw new Error(`Browser errors: ${errors.join(" | ")}`);
  console.log("E2E upload flow: PASS");
} finally {
  await browser.close();
}
