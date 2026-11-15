"""core/resources.py — sizing the renderer to the container's real memory limit."""

from __future__ import annotations

from clipmaker.core.resources import cpu_count, encoder_threads, memory_limit_mb


def test_encoder_threads_fit_the_memory_budget() -> None:
    from clipmaker.core.resources import render_slots

    assert encoder_threads(budget_mb=256) == 1  # tiny container: one thread, never killed
    assert encoder_threads(budget_mb=512) == 1
    # Never more work in flight than the box has CPUs to spare for it.
    assert render_slots() * encoder_threads(budget_mb=16000) <= max(1, cpu_count() - 1)
    assert encoder_threads(budget_mb=None) >= 1  # uncapped host


def test_limit_reads_without_crashing() -> None:
    limit = memory_limit_mb()
    assert limit is None or limit > 0
    assert cpu_count() >= 1


def test_render_slots_leave_a_cpu_for_the_site(monkeypatch) -> None:
    from clipmaker.core import resources

    for cpus, slots in ((1, 1), (2, 1), (4, 3), (8, 4), (16, 4)):
        monkeypatch.setattr(resources, "cpu_count", lambda c=cpus: c)
        assert resources.render_slots() == slots
        # Threads are shared between the clips rendering at once, never oversubscribed.
        assert resources.render_slots() * resources.encoder_threads(budget_mb=16000) <= max(
            1, cpus - 1
        )
