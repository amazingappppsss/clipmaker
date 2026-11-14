"""TRANSCRIBING: speech → timed words → sentence segments, stored in transcripts tables.

Idempotent: an existing transcript for the project is reused (never paid for twice).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from clipmaker.db.models import Project, Transcript, TranscriptSegment
from clipmaker.pipeline.context import StageContext, StageOutput
from clipmaker.pipeline.errors import PermanentStageError, RetryableStageError
from clipmaker.pipeline.transcript import build_segments
from clipmaker.providers.transcription.base import TranscriptionError


def run(ctx: StageContext) -> StageOutput:
    with ctx.sessions() as db:
        existing = db.query(Transcript).filter_by(project_id=ctx.project_id).one_or_none()
        if existing is not None:
            return StageOutput({"transcript_id": str(existing.id)}, skipped=True)
        project = db.get(Project, ctx.project_id)
        settings: dict[str, Any] = dict(project.settings) if project else {}
    language = settings.get("language")
    language = None if language in (None, "auto") else str(language)

    audio_path = ctx.work_dir / "audio.mp3"
    if not audio_path.is_file():
        ctx.storage.download_file(f"{ctx.prefix}work/audio.mp3", audio_path)

    try:
        result = ctx.transcriber().transcribe(audio_path, language, ctx.heartbeat)
    except TranscriptionError as exc:
        error = RetryableStageError if exc.retryable else PermanentStageError
        raise error("transcription_failed", str(exc)) from exc

    segments = build_segments(result.words)
    if not segments:
        raise PermanentStageError("no_speech", "We couldn't find any speech in this video.")

    raw_key = f"{ctx.prefix}work/transcript_raw.json"
    raw_path = ctx.work_dir / "transcript_raw.json"
    raw_path.write_text(
        json.dumps({"meta": result.raw, "words": [asdict(w) for w in result.words]})
    )
    ctx.storage.upload_file(raw_path, raw_key, "application/json")

    with ctx.sessions() as db:
        transcript = Transcript(
            project_id=ctx.project_id,
            provider=result.provider,
            model=result.model,
            language=result.language,
            duration_seconds=result.duration_seconds,
            full_text=" ".join(s.text for s in segments),
            has_word_timestamps=True,
            has_speakers=result.has_speakers,
            raw_key=raw_key,
        )
        transcript.segments = [
            TranscriptSegment(
                idx=s.idx,
                start_seconds=s.start,
                end_seconds=s.end,
                speaker=s.speaker,
                text=s.text,
                words=[{"w": w.text, "s": w.start, "e": w.end, "p": w.confidence} for w in s.words],
            )
            for s in segments
        ]
        db.add(transcript)
        db.commit()
        transcript_id = str(transcript.id)
    return StageOutput(
        {"transcript_id": transcript_id, "segments": len(segments), "language": result.language},
        cost_usd=result.cost_usd,
    )
