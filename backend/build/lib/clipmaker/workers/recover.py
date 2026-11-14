"""Resume interrupted jobs right after a restart (single-node deployments).

When the one container restarts (e.g. a redeploy), any job it was running is orphaned: its lease
names a worker that no longer exists. Waiting for the lease to expire costs users up to 15
minutes, so the start script runs this *before* the new worker starts: it clears those leases
and re-queues the jobs at once. Completed stages are kept, so work resumes where it stopped.

Only safe when no other worker can be running — start-single-node.sh guarantees that.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from sqlalchemy import update
from sqlalchemy.orm import Session

from clipmaker.core.enums import TERMINAL_STATES
from clipmaker.db.models import ProcessingJob

logger = logging.getLogger(__name__)

# Finished runs (including NEEDS_REVIEW, a pause before unbuilt stages) are left alone.
_RESTING = TERMINAL_STATES


def recover_interrupted_jobs(db: Session, enqueue: Callable[[uuid.UUID], None]) -> list[uuid.UUID]:
    """Release every lease on unfinished jobs and queue them again. Returns the job ids."""
    ids = list(
        db.scalars(
            update(ProcessingJob)
            .where(ProcessingJob.state.notin_(_RESTING))
            .values(lease_owner=None, lease_expires_at=None)
            .returning(ProcessingJob.id)
        ).all()
    )
    db.commit()
    for job_id in ids:
        logger.warning("resume_interrupted_job", extra={"job_id": str(job_id)})
        enqueue(job_id)
    return ids


def main() -> None:
    from clipmaker.db.session import get_session_factory
    from clipmaker.workers.tasks import enqueue_job

    with get_session_factory()() as db:
        ids = recover_interrupted_jobs(db, enqueue_job)
    print(f"Resumed {len(ids)} interrupted job(s).")


if __name__ == "__main__":
    main()
