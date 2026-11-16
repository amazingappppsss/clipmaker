"""Helpers shared by the AI stages: loading segments and splitting very long transcripts."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from clipmaker.db.models import Transcript
from clipmaker.pipeline.context import StageContext
from clipmaker.pipeline.errors import PermanentStageError
from clipmaker.pipeline.transcript import Segment
from clipmaker.providers.transcription.base import Word

# ~150K tokens of rendered transcript per call (≈4 chars/token). Models accept far more, but
# smaller windows keep attention sharp and latency low. A 4-hour podcast usually fits in one.
MAX_WINDOW_CHARS = 600_000
WINDOW_OVERLAP_SEGMENTS = 40  # shared context so moments at a seam are seen whole


def load_segments(ctx: StageContext) -> list[Segment]:
    """Segments (with words) for this project, ordered by index."""
    with ctx.sessions() as db:
        transcript = db.query(Transcript).filter_by(project_id=ctx.project_id).one_or_none()
        if transcript is None:
            raise PermanentStageError(
                "no_transcript", "Transcript missing; transcription must run first."
            )
        return [
            Segment(
                idx=s.idx,
                start=s.start_seconds,
                end=s.end_seconds,
                speaker=s.speaker,
                words=[
                    Word(
                        text=w["w"],
                        start=w["s"],
                        end=w["e"],
                        confidence=w.get("p", 1.0),
                        speaker=s.speaker,
                    )
                    for w in s.words
                ],
            )
            for s in transcript.segments
        ]


# Candidate hunting is split into parts that run at the same time: one long call over a whole
# transcript is the slowest thing in the pipeline, and the model judges each moment locally
# anyway (the whole-video analysis it also gets supplies the context).
PARALLEL_TARGET_CHARS = 9_000  # ~3 minutes of talk per part
MIN_PARALLEL_CHARS = 7_000  # below this, one call is already quick
#: How many parts of a transcript are hunted at once.
#:
#: This was 4, which quietly punished exactly the videos we are built for. The parts are
#: sized to PARALLEL_TARGET_CHARS, so a long episode wants more of them — a two-hour podcast
#: wants about twelve. Capping at four did not make it cheaper, it made each part three times
#: the intended size, and selection ran three times longer than it needed to.
#:
#: These calls wait on the network, not the CPU, so more of them at once costs no machine.
#: The ceiling exists for the provider's rate limits, and is settings-backed so it can be
#: tuned against a real job without a deploy.
MAX_PARALLEL_PARTS = 8
PART_OVERLAP_SEGMENTS = 6


def split_for_parallel(
    segments: list[Segment], rendered_lengths: list[int], max_parts: int = MAX_PARALLEL_PARTS
) -> list[tuple[int, int]]:
    """Overlapping [start, end] parts to hunt for candidates in at the same time (pure)."""
    total = sum(rendered_lengths)
    if total < MIN_PARALLEL_CHARS or len(segments) < 2 * max_parts:
        return [(0, len(segments) - 1)]
    parts = max(2, min(max_parts, -(-total // PARALLEL_TARGET_CHARS)))
    size = len(segments) / parts
    spans: list[tuple[int, int]] = []
    for i in range(parts):
        start = max(0, int(i * size) - (PART_OVERLAP_SEGMENTS if i else 0))
        end = len(segments) - 1 if i == parts - 1 else int((i + 1) * size) - 1
        if end > start:
            spans.append((start, end))
    return spans or [(0, len(segments) - 1)]


def parallel_parts(settings: Any | None = None) -> int:
    """How many parts to hunt at once, from settings when we have them."""
    value = getattr(settings, "llm_parallel_parts", None) if settings else None
    return max(1, int(value)) if value else MAX_PARALLEL_PARTS


def run_parallel[T](tasks: list[Callable[[], T]], workers: int = MAX_PARALLEL_PARTS) -> list[T]:
    """Run independent LLM calls at the same time, keeping their order. Errors propagate."""
    if len(tasks) == 1:
        return [tasks[0]()]
    with ThreadPoolExecutor(max_workers=min(workers, len(tasks))) as pool:
        return [f.result() for f in [pool.submit(t) for t in tasks]]


def windows(segments: list[Segment], rendered_lengths: list[int]) -> list[tuple[int, int]]:
    """Split into overlapping [start, end] windows under MAX_WINDOW_CHARS (pure)."""
    if sum(rendered_lengths) <= MAX_WINDOW_CHARS:
        return [(0, len(segments) - 1)]
    result: list[tuple[int, int]] = []
    start = 0
    while start < len(segments):
        size, end = 0, start
        while end < len(segments) and size + rendered_lengths[end] <= MAX_WINDOW_CHARS:
            size += rendered_lengths[end]
            end += 1
        end = max(end - 1, start)
        result.append((start, end))
        if end >= len(segments) - 1:
            break
        start = max(end - WINDOW_OVERLAP_SEGMENTS + 1, start + 1)
    return result


def local_source(ctx: StageContext, key: str) -> str:
    """A local file path for a stored video, downloading it once per job when storage is remote.

    FFmpeg can stream from a URL, but face tracking (OpenCV) and many seeks are far faster and
    more reliable on a local file. The copy lives in the job's work dir (deleted afterwards).
    """
    source = ctx.storage.media_source(key)
    if not source.startswith(("http://", "https://")):
        return source
    local = ctx.work_dir / ("source" + Path(key).suffix)
    if not local.is_file():
        ctx.storage.download_file(key, local)
    return str(local)
