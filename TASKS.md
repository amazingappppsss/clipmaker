# Tasks

Legend: ✅ done · 🔜 next · ⏳ later · ⚠️ needs a decision from the owner

## Milestone 1 — Foundation ✅
- ✅ Monorepo layout, docs, `.env.example`, Docker Compose, CI
- ✅ FastAPI app: config, structured JSON logs, typed errors, CORS, request IDs, health check
- ✅ Supabase JWT verification (JWKS + HS256) and dev-only login
- ✅ PostgreSQL schema for all 13 tables + Alembic migration (up/down tested)
- ✅ Object storage abstraction: local (HMAC-signed URLs) and S3/R2 (presigned URLs)
- ✅ Projects API: create / list (cursor pagination) / get / delete (removes files)
- ✅ Direct-to-storage uploads with server verification (size, ffprobe, audio, duration)
- ✅ Credit ledger with free-trial grant; public plan catalog
- ✅ Per-user rate limiting
- ✅ Frontend: landing page, login, dashboard, new project (real upload progress), project page, account
- ✅ Shared TS types generated from the backend contract
- ✅ Tests: 46 backend (pytest), 29 frontend (vitest), browser smoke test

## Milestone 2 — Core AI pipeline 🔜
- 🔜 Pipeline runner: job lease, idempotent stages, per-stage retries, crash recovery
- 🔜 `POST /projects/{id}/process`, `GET /projects/{id}/status` (debit credits, refund on failure)
- 🔜 INGESTING: thumbnail, audio extraction (16 kHz mono)
- 🔜 Transcription provider interface + implementation with word timestamps; chunking with overlap
- 🔜 Full-video understanding (sections with overlapping context → global analysis)
- 🔜 Candidate generation, weighted scoring (configurable weights), dedupe, selection
- ⚠️ Choose AI providers and approve API costs (LLM for understanding; transcription)

## Milestone 3 — Video editing ⏳
- Trim + dead-air removal, face detection, smoothed 9:16 reframing, ASS subtitles (2 styles),
  opening titles, loudness normalisation, H.264 1080×1920 render

## Milestone 4 — Quality and reliability ⏳
- Technical / content / visual QA checks, bounded repair loop, NEEDS_REVIEW
- Cost tracking per job, error tracking (Sentry), stale-job reaper

## Milestone 5 — SaaS experience ⏳
- Results page (preview, download, captions, hashtags, regenerate)
- ⚠️ Payment provider for India (Razorpay vs Stripe India) — verify availability first

## Milestone 6 — End-to-end validation ⏳
- Test-video dataset; 30-minute podcast → 5 useful clips; failure-injection tests
- Replace landing illustration with real before/after examples

## Technical debt
- Uploads are single PUT (≤ 5 GiB) and not resumable → add S3 multipart presigned parts.
- URL ingestion not implemented (PRD: only authorized, reliable sources).
- Pending landing-page upload is lost on a full-page magic-link redirect (user re-selects the file).
- Free credits are a one-time trial grant; monthly renewal comes with billing (M5).
