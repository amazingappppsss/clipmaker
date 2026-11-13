# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com).

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
