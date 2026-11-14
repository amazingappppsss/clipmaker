"""Helpers shared by the AI stages: loading segments and splitting very long transcripts."""

from __future__ import annotations

from pathlib import Path

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
