"""Health check used by Docker, load balancers and uptime monitors."""

from __future__ import annotations

import redis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from clipmaker import __version__
from clipmaker.api.deps import AppSettings, DbSession
from clipmaker.schemas import HealthOut

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
        status="ok" if ok else "degraded", database=db_ok, redis=redis_ok, version=__version__
    )
