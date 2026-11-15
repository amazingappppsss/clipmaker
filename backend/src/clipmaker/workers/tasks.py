"""Celery tasks: run a processing job, and periodically recover jobs from crashed workers."""

from __future__ import annotations

import logging
import socket
import uuid
from datetime import timedelta
from typing import Any

from clipmaker.core.config import get_settings
from clipmaker.db.session import get_session_factory
from clipmaker.pipeline.runner import JobRunner, Outcome
from clipmaker.services.housekeeping import make_room
from clipmaker.services.processing import stale_job_ids
from clipmaker.storage.factory import get_storage
from clipmaker.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=10)
# Keep at least this much room ready for the next import.
KEEP_FREE_BYTES = 500 * 1024 * 1024


def enqueue_job(job_id: uuid.UUID) -> None:
    """Queue a job for processing (used by the API)."""
    run_processing_job.delay(str(job_id))


# Celery ships without type hints, hence the targeted ignores on its decorators.
@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True, name="clipmaker.workers.tasks.run_processing_job", max_retries=None
)
def run_processing_job(self: Any, job_id: str) -> str:
    """Run (or resume) a job. Retries are scheduled by the runner's own attempt accounting."""
    worker_id = f"{socket.gethostname()}:{self.request.id}"
    runner = JobRunner(
        uuid.UUID(job_id), worker_id, get_settings(), get_storage(), get_session_factory()
    )
    outcome, delay = runner.run()
    if outcome == Outcome.RETRY:
        raise self.retry(countdown=delay)
    return outcome.value


@celery_app.task(name="clipmaker.workers.tasks.reap_stale_jobs")  # type: ignore[untyped-decorator]
def reap_stale_jobs() -> int:
    """Re-queue jobs whose worker died mid-run, and keep the disk from filling up.

    Clearing space on a schedule means a download never arrives to find a full disk, even
    after a run was cancelled or the container restarted mid-job.
    """
    with get_session_factory()() as db:
        ids = stale_job_ids(db, STALE_AFTER)
    for job_id in ids:
        logger.warning("requeue_stale_job", extra={"job_id": str(job_id)})
        enqueue_job(job_id)

    settings = get_settings()
    if settings.storage_backend.value == "local":
        with get_session_factory()() as db:
            freed = make_room(db, get_storage(), settings.local_storage_dir, KEEP_FREE_BYTES)
        if freed:
            logger.info("housekeeping_freed_files", extra={"files": freed})
    return len(ids)
