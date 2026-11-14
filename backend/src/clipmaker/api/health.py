"""Health check used by Docker, load balancers and uptime monitors."""

from __future__ import annotations

import os
from datetime import datetime

import redis
from fastapi import APIRouter, Response, status
from pydantic import SecretStr
from sqlalchemy import select, text

from clipmaker import __version__
from clipmaker.api.deps import AppSettings, DbSession
from clipmaker.db.models import ProcessingJob
from clipmaker.schemas import HealthOut
from clipmaker.storage.factory import get_storage
from clipmaker.storage.local import LocalStorage

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: DbSession, settings: AppSettings, response: Response) -> HealthOut:
    """Report dependency status; 503 when any dependency is down."""
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    try:
        redis_ok = bool(redis.Redis.from_url(settings.redis_url, socket_timeout=0.5).ping())
    except redis.RedisError:
        redis_ok = False
    ok = db_ok and redis_ok
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthOut(
        status="ok" if ok else "degraded",
        database=db_ok,
        redis=redis_ok,
        version=__version__,
        commit=(os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "")[:7] or None,
        transcription_ready=_has(settings.assemblyai_api_key),
        llm_ready=_has(settings.anthropic_api_key),
        link_import_ready=settings.enable_url_import and _has(settings.apify_token),
        storage_base_url=storage_base_url(),
        storage_persistent=_persistent(settings),
        recent_stage_seconds=_recent_timings(db) if db_ok else [],
        recent_failures=_recent_failures(db) if db_ok else [],
    )


def _has(secret: SecretStr | None) -> bool:
    return bool(secret and secret.get_secret_value().strip())


def storage_base_url() -> str | None:
    """Where signed upload links point for this request (None when not using local storage)."""
    storage = get_storage()
    return storage.base_url() if isinstance(storage, LocalStorage) else None


def _persistent(settings: AppSettings) -> bool | None:
    """Local storage under the platform volume survives redeploys; None if not on such a host."""
    mount = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if settings.storage_backend.value != "local":
        return True
    if not mount:
        return None
    return os.path.abspath(settings.local_storage_dir).startswith(os.path.abspath(mount))


def _recent_timings(db: DbSession, limit: int = 5) -> list[dict[str, float]]:
    """Per-stage durations of the latest runs (no user data, just seconds)."""
    jobs = db.scalars(
        select(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(limit)
    ).all()
    out: list[dict[str, float]] = []
    for job in jobs:
        row: dict[str, float] = {}
        for stage, rec in (job.stages or {}).items():
            try:
                start = datetime.fromisoformat(rec["started_at"])
                end = datetime.fromisoformat(rec["finished_at"])
            except (KeyError, TypeError, ValueError):
                continue
            row[stage] = round((end - start).total_seconds(), 1)
        if row:
            out.append(row)
    return out


def _recent_failures(db: DbSession, limit: int = 5) -> list[dict[str, str | int]]:
    """Failed stages of the latest runs: stage name, error code, attempt (diagnostics)."""
    jobs = db.scalars(
        select(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(limit)
    ).all()
    out: list[dict[str, str | int]] = []
    for job in jobs:
        for stage, rec in (job.stages or {}).items():
            if rec.get("status") != "failed" and not (rec.get("error") and rec.get("attempts")):
                continue
            code = str(rec.get("error") or "").split(":", 1)[0][:40]
            if code:
                out.append({"stage": stage, "code": code, "attempts": int(rec.get("attempts", 0))})
    return out
