#!/usr/bin/env bash
# Generate frontend types from the backend API contract.
#   backend/src/clipmaker/schemas.py (Pydantic)  ->  OpenAPI JSON  ->  common/types/api.ts
# Run after changing any backend schema or route. CI fails if the output is stale.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$ROOT/backend/.venv/bin/python}"
OUT_DIR="$ROOT/common/types"
mkdir -p "$OUT_DIR"

# Import the app with safe placeholder settings (no DB connection is made at import time).
( cd "$ROOT/backend" && APP_ENV=test ENABLE_DEV_AUTH=true STORAGE_BACKEND=local \
  SUPABASE_JWT_SECRET=gen-types-placeholder-secret-0000000000 \
  "$PY" -c "import json; from clipmaker.main import app; print(json.dumps(app.openapi(), indent=2))" \
) > "$OUT_DIR/openapi.json"

npx --no-install openapi-typescript "$OUT_DIR/openapi.json" -o "$OUT_DIR/api.ts" >/dev/null
echo "Generated $OUT_DIR/api.ts"
