"""How much longer a job will take, so the page can show a real countdown.

Rates are seconds of work per minute of source video (or per clip for the render stages),
measured on the production container. They are deliberately simple and honest: an estimate
from measured rates beats a spinner that says nothing, and the number only ever counts work
that has not been done yet.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from clipmaker.core.enums import PIPELINE_STAGES, ProjectState

# seconds per minute of source video
PER_MINUTE: dict[ProjectState, float] = {
    ProjectState.INGESTING: 1.8,
    ProjectState.TRANSCRIBING: 0.9,
    ProjectState.UNDERSTANDING: 2.7,
    ProjectState.SELECTING: 10.5,
    ProjectState.EDITING: 1.5,
}
# seconds per clip
PER_CLIP: dict[ProjectState, float] = {
    ProjectState.RENDERING: 22.0,
    ProjectState.QUALITY_CHECK: 2.0,
}
MIN_CLIPS = 3  # before selection runs we don't know the count yet


def stage_estimate(stage: ProjectState, minutes: float, clips: int) -> float:
    """Expected seconds for one stage."""
    if stage in PER_CLIP:
        return PER_CLIP[stage] * max(clips, MIN_CLIPS)
    return PER_MINUTE.get(stage, 0.0) * max(minutes, 0.5)


def remaining_seconds(
    stages: dict[str, Any],
    duration_seconds: float | None,
    clips: int,
    now: datetime | None = None,
) -> int | None:
    """Seconds of work left, or None when nothing is running (pure, unit-tested)."""
    if not duration_seconds:
        return None
    minutes = duration_seconds / 60
    moment = now or datetime.now(UTC)
    total = 0.0
    running = False
    for stage in PIPELINE_STAGES:
        record = stages.get(stage.value) or {}
        status = record.get("status")
        if status == "done":
            continue
        estimate = stage_estimate(stage, minutes, clips)
        if status == "running":
            running = True
            started = record.get("started_at")
            try:
                elapsed = (moment - datetime.fromisoformat(str(started))).total_seconds()
            except (TypeError, ValueError):
                elapsed = 0.0
            # Never promise a finish that has already passed: a slow stage keeps 10s on the
            # clock rather than counting down to zero and sitting there.
            total += max(estimate - max(elapsed, 0.0), 10.0)
        else:
            total += estimate
    return round(total) if (running or total) else None
