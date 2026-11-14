"""Celery application: background workers run separately from the web API (PRD §7).

Queues:
* `pipeline` — I/O- and API-bound stages (ingest, transcription, AI analysis, QA).
* `render`   — CPU-heavy FFmpeg/OpenCV rendering; scale these workers independently.

Reliability settings: tasks are acknowledged only after they finish (`acks_late`) and are
re-queued if the worker process dies (`reject_on_worker_lost`), so a crash never loses work.
Pipeline tasks are registered in Milestone 2 (`clipmaker.workers.tasks`).
"""

from __future__ import annotations

from celery import Celery

from clipmaker.core.config import get_settings
from clipmaker.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

celery_app = Celery("clipmaker", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # long tasks: never hoard jobs on one worker
    task_default_queue="pipeline",
    task_routes={"clipmaker.workers.tasks.render_*": {"queue": "render"}},
    task_serializer="json",
    accept_content=["json"],
    result_expires=24 * 3600,
    broker_transport_options={"visibility_timeout": 4 * 3600},  # > longest task
    worker_hijack_root_logger=False,
)
# Crash recovery: re-queue jobs whose worker died (see workers/tasks.py::reap_stale_jobs).
celery_app.conf.beat_schedule = {
    "reap-stale-jobs": {"task": "clipmaker.workers.tasks.reap_stale_jobs", "schedule": 300.0},
}
celery_app.autodiscover_tasks(["clipmaker.workers"], force=True)
