# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com).

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
