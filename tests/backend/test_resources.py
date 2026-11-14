"""core/resources.py — sizing the renderer to the container's real memory limit."""

from __future__ import annotations

from clipmaker.core.resources import cpu_count, encoder_threads, memory_limit_mb


def test_encoder_threads_fit_the_memory_budget() -> None:
    assert encoder_threads(budget_mb=256) == 1  # tiny container: one thread, never killed
    assert encoder_threads(budget_mb=512) == 1
    assert encoder_threads(budget_mb=2048) == min(4, cpu_count())
    assert encoder_threads(budget_mb=8192) == min(4, cpu_count())
    assert encoder_threads(budget_mb=None) == min(4, cpu_count())  # uncapped host


def test_limit_reads_without_crashing() -> None:
    limit = memory_limit_mb()
    assert limit is None or limit > 0
    assert cpu_count() >= 1
