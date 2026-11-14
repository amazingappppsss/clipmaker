"""What this container is actually allowed to use.

Hosts (Railway, Fly, Render, Kubernetes) cap memory with cgroups and kill any process that
goes over — with no error message, which is impossible to debug from the outside. Reading the
real limit lets the renderer size itself to fit instead of guessing, so it is never killed.
"""

from __future__ import annotations

import os
from pathlib import Path

# cgroup v2 first, then v1. "max" (v2) or a huge number (v1) means "no limit set".
_LIMIT_FILES = (
    Path("/sys/fs/cgroup/memory.max"),
    Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
)
_USAGE_FILES = (
    Path("/sys/fs/cgroup/memory.current"),
    Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"),
)
_NO_LIMIT = 1 << 53  # bigger than any real container limit


def _read(paths: tuple[Path, ...]) -> int | None:
    for path in paths:
        try:
            raw = path.read_text().strip()
        except OSError:
            continue
        if raw == "max":
            return None
        try:
            value = int(raw)
        except ValueError:
            continue
        return None if value >= _NO_LIMIT else value
    return None


def memory_limit_mb() -> int | None:
    """Hard memory limit for this container in MB, or None when it isn't capped."""
    limit = _read(_LIMIT_FILES)
    return limit // (1024 * 1024) if limit else None


def memory_used_mb() -> int | None:
    """Memory currently charged to this container in MB (None when not measurable)."""
    used = _read(_USAGE_FILES)
    return used // (1024 * 1024) if used else None


def cpu_count() -> int:
    """Usable CPUs, honouring any cgroup CPU quota the host applies."""
    try:
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if quota != "max":
            return max(1, int(int(quota) / int(period)))
    except (OSError, ValueError):
        pass
    return max(1, len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 1)


def encoder_threads(budget_mb: int | None = None) -> int:
    """How many encoder threads fit in the memory we have.

    Measured at 1080x1920: ~200 MB for FFmpeg and the first thread, ~120 MB per extra thread.
    Only half the container's memory is spent here, since the API, the worker and the page
    cache share it — and a host kills the whole process the moment the cap is crossed.
    """
    limit = budget_mb if budget_mb is not None else memory_limit_mb()
    if limit is None:
        return min(4, cpu_count())
    spare = max(0, limit // 2 - 200)
    return max(1, min(cpu_count(), 1 + spare // 120, 4))
