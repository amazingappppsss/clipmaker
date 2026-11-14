# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com).

## 0.3.0 — Milestone 3: finished vertical shorts

- **Editing engine** (`backend/src/clipmaker/editing/`):
  - **Smart cuts** remove dead air between words while keeping the natural rhythm and the
    pause before a reveal.
  - **Speaker-following 9:16 crop**: YuNet face detection plus a lip-motion active-speaker
    signal, with punch-in zooms so the shot changes at least every 6 s.
  - **Animated captions** (ASS, Montserrat Black): the spoken word pops in lime, and numbers
    and names stay highlighted. The hook title sits in a lime box for the first 3 s.
  - **Flash-forward hook**: the teaser plays, flashes white, then the clip starts.
  - **Render**: 1080×1920 H.264 MP4 with audio normalised to -14 LUFS, seeked straight to the
    clip, so a moment at minute 90 of a long video renders as fast as one at minute 1.
- **Pipeline**: the new EDITING, RENDERING and QUALITY_CHECK stages are idempotent. Projects
  now finish as COMPLETED, and only clips that pass QA can be downloaded.
- **API**: ready clips include signed `video_url`, `download_url` and `thumbnail_url`.
- **Web**: a vertical player and a Download MP4 button on each clip, and all 7 steps show
  live progress.
- **Bundled assets**: the YuNet face model (MIT) and Montserrat (SIL OFL).

## [0.2.0] — 2026-11-13 — Milestone 2: AI clip selection + link import

### Added
- Processing pipeline: job lease, idempotent stages, bounded retries, crash recovery (stale-job
  reaper), credit debit on start and automatic refund on failure.
- Transcription via AssemblyAI (word timings + speaker labels).
- Full-video understanding and clip selection with Claude (Opus 5.5 for the hard judgment,
  Haiku 5.5 for titles/captions/hashtags), prompt caching, structured outputs, refusal fallback.
- Editorial rules in code: configurable weighted scoring, whole-sentence boundaries, 20-90 s
  limits, dedupe, quality bar.
- YouTube link import (landing hero + New Project "Paste link" tab) with rights confirmation,
  host allow-list, background download and `ENABLE_URL_IMPORT` kill switch.
- Project page: "Find my clips", live per-stage status, picked moments with in-browser preview.
- Railway single-node deployment with a plain-English startup self-check.
- USD pricing for the international launch (Free 15 min, Starter $15, Pro $29).

## [0.1.0] — 2026-11-13 — Milestone 1: Foundation

### Added
- Backend (FastAPI): projects and upload API, account usage, public plans, health check,
  Supabase JWT auth, per-user rate limiting, structured logging, typed error responses.
- Database: 13-table PostgreSQL schema with Alembic migration.
- Storage: local (dev) and S3/Cloudflare R2 backends with signed upload/download URLs.
- Upload verification with FFprobe: file size, readability, audio track, duration limits.
- Credit ledger with a 60-credit free trial.
- Frontend (Next.js 16): landing page, sign-in (Supabase or dev), dashboard, new-project upload
  with real progress, project page with real processing stages, account page.
- Shared TypeScript types generated from the backend's OpenAPI schema.
- Docker images, Docker Compose stack, GitHub Actions CI.
- Tests: pytest (backend), Vitest (frontend), Playwright smoke test.
