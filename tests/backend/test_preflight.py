"""preflight.py — the startup checklist passes on a healthy setup."""

from __future__ import annotations

import pytest

from clipmaker import preflight


def test_preflight_passes_with_working_services(capsys: pytest.CaptureFixture[str]) -> None:
    assert preflight.main() == 0
    out = capsys.readouterr().out
    assert "[OK]   database reachable" in out
    assert "[OK]   redis reachable" in out
    assert "All checks passed." in out
    assert "ANTHROPIC_API_KEY is missing" in out  # warns, but does not block
