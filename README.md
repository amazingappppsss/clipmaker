# ClipMaker

**Paste a video. Get finished shorts.** An autonomous AI editor that turns long-form videos and
podcasts into ready-to-post vertical clips — with speaker-aware framing, captions, hooks and
automated quality checks.

> Status: **Milestone 1 (Foundation) complete** — auth, database, storage, uploads, landing page
> and app shell. The AI clipping pipeline is Milestone 2. See [TASKS.md](TASKS.md).

| Doc | What's in it |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | structure, layer rules, data model, decisions |
| [TASKS.md](TASKS.md) | milestone checklist and known technical debt |
| [CHANGELOG.md](CHANGELOG.md) | what changed, per milestone |
| [.env.example](.env.example) | every configuration variable, explained |

## Stack

Next.js 16 · TypeScript · Tailwind v4 — FastAPI · SQLAlchemy · Alembic — PostgreSQL (Supabase)
· Supabase Auth — Cloudflare R2 (S3-compatible) — Redis · Celery — FFmpeg · OpenCV.

## Quick start (Docker)

```bash
docker compose up --build
```

Open http://localhost:3000 and use the development login (any email). Uses local storage and
dev auth — no cloud accounts needed.

## Local development (without Docker)

Requirements: Python 3.12+, Node 22+, PostgreSQL 16, Redis 7, FFmpeg.

```bash
# 1. Database
createuser -P clipmaker          # password: clipmaker
createdb -O clipmaker clipmaker
createdb -O clipmaker clipmaker_test

# 2. Backend
cd backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp ../.env.example .env          # keep only the backend section
.venv/bin/alembic upgrade head
.venv/bin/uvicorn clipmaker.main:app --reload            # http://localhost:8000/docs

# 3. Frontend (from the repository root)
npm install
printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\nNEXT_PUBLIC_DEV_AUTH=true\n' > frontend/.env.local
npm run dev:web                                           # http://localhost:3000
```

## Tests and checks

```bash
cd backend && .venv/bin/pytest && .venv/bin/ruff check src ../tests/backend && .venv/bin/mypy src
npm run test:web && npm run lint:web && npm run typecheck:web
node tests/e2e/upload-flow.mjs   # browser smoke test; needs both servers running
```

After changing any backend schema or route, regenerate the shared types:

```bash
npm run gen:types
```

## Going to production (checklist)

1. **Supabase** project: set `SUPABASE_URL` (backend) and `NEXT_PUBLIC_SUPABASE_URL` +
   `NEXT_PUBLIC_SUPABASE_ANON_KEY` (frontend). Enable Email and Google providers and add your
   site URL to the redirect allow-list. Point `DATABASE_URL` at the Supabase Postgres.
2. **Cloudflare R2** bucket: `STORAGE_BACKEND=s3`, `S3_ENDPOINT_URL`, `S3_BUCKET`, keys. Add a
   CORS rule allowing `PUT` and `GET` from your site origin.
3. Set `APP_ENV=production`, `ENABLE_DEV_AUTH=false`, `NEXT_PUBLIC_DEV_AUTH=false`, a strong
   `STORAGE_SIGNING_KEY`, and `CORS_ORIGINS` to your domain. The API refuses to start with
   unsafe settings.
4. Run `alembic upgrade head` as a release step, then deploy `api`, `worker` and `web`.

## Responsible use

Only upload videos you own or have rights to. URL ingestion will only support sources that can
be accessed legally and reliably.
