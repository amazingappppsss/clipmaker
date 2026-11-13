#!/usr/bin/env bash
# Single-node runtime: database migrations, then the API and the background worker side by side.
# If either process exits, the container exits too so the platform restarts it (no zombie halves).
set -euo pipefail

# Plain-English checklist of settings, database, Redis, storage and keys; stops on a blocker.
python -m clipmaker.preflight

alembic upgrade head

celery -A clipmaker.workers.celery_app worker --beat --schedule /tmp/celerybeat-schedule \
  -Q pipeline,render --concurrency "${WORKER_CONCURRENCY:-2}" --loglevel INFO &
WORKER_PID=$!

uvicorn clipmaker.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers \
  --forwarded-allow-ips '*' &
API_PID=$!

trap 'kill -TERM "$WORKER_PID" "$API_PID" 2>/dev/null' TERM INT
wait -n "$WORKER_PID" "$API_PID" || true  # non-zero status must not skip cleanup (set -e)
echo "A process exited; stopping the container so it restarts cleanly." >&2
kill -TERM "$WORKER_PID" "$API_PID" 2>/dev/null || true
wait
exit 1
