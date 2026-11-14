"""UNDERSTANDING: full-video analysis (PRD §5.3) with the smart model.

Idempotent: an existing VideoAnalysis is reused. Long transcripts are analysed per overlapping
window and merged, preserving segment indexes so every moment keeps its timestamps.
"""

from __future__ import annotations

from decimal import Decimal
from functools import partial
from typing import Any

from clipmaker.db.models import VideoAnalysis
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError, RetryableStageError
from clipmaker.pipeline.prompts import (
    ANALYSIS_INSTRUCTION,
    ANALYSIS_SCHEMA,
    PROMPT_VERSION,
    SYSTEM_EDITOR,
)
from clipmaker.pipeline.stages.common import load_segments, run_parallel, windows
from clipmaker.pipeline.transcript import render_for_llm
from clipmaker.providers.llm.base import LLMError, LLMRequest


def merge_analyses(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine per-window analyses into one (pure)."""
    if len(parts) == 1:
        return parts[0]
    seen: set[tuple[int, int]] = set()
    moments = []
    for part in parts:
        for m in part.get("notable_moments", []):
            key = (m["start_segment"], m["end_segment"])
            if key not in seen:
                seen.add(key)
                moments.append(m)
    speakers: dict[str, dict[str, Any]] = {}
    for part in parts:
        for sp in part.get("speakers", []):
            speakers.setdefault(sp["label"], sp)
    return {
        "summary": " ".join(p.get("summary", "") for p in parts).strip(),
        "content_type": parts[0].get("content_type", "other"),
        "speakers": list(speakers.values()),
        "topics": list(dict.fromkeys(t for p in parts for t in p.get("topics", []))),
        "sections": [s for p in parts for s in p.get("sections", [])],
        "notable_moments": sorted(moments, key=lambda m: m["start_segment"]),
    }


def run(ctx: StageContext) -> StageOutput:
    with ctx.sessions() as db:
        existing = db.query(VideoAnalysis).filter_by(project_id=ctx.project_id).one_or_none()
        if existing is not None:
            return StageOutput({"analysis_id": str(existing.id)}, skipped=True)

    segments = load_segments(ctx)
    lengths = [len(render_for_llm([s])) + 1 for s in segments]

    def analyse(span: tuple[int, int]) -> Any:
        start, end = span
        try:
            return ctx.llm().complete_json(
                LLMRequest(
                    # Summarising a transcript is work the fast model does well, and it keeps
                    # this stage off the critical path before clip hunting starts.
                    tier="fast",
                    system=SYSTEM_EDITOR,
                    context=render_for_llm(segments[start : end + 1]),
                    instruction=ANALYSIS_INSTRUCTION,
                    schema=ANALYSIS_SCHEMA,
                )
            )
        except LLMError as exc:
            error = RetryableStageError if exc.retryable else PermanentStageError
            raise error("analysis_failed", str(exc)) from exc

    results = run_parallel([partial(analyse, span) for span in windows(segments, lengths)])
    parts: list[dict[str, Any]] = [r.data for r in results]
    cost = sum((r.cost_usd for r in results), Decimal(0))
    model = results[-1].model if results else ""
    ctx.heartbeat()

    analysis = merge_analyses(parts)
    with ctx.sessions() as db:
        row = VideoAnalysis(
            project_id=ctx.project_id,
            provider=ctx.llm().name,
            model=model,
            version=PROMPT_VERSION,
            analysis=analysis,
        )
        db.add(row)
        db.commit()
        analysis_id = str(row.id)
    return StageOutput(
        {
            "analysis_id": analysis_id,
            "windows": len(parts),
            "moments": len(analysis.get("notable_moments", [])),
        },
        cost_usd=cost,
    )
