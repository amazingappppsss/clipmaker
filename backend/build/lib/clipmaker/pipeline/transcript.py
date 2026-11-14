"""Turn timed words into sentence segments, and render them for the LLM.

Segments are the atoms clips are cut on: a clip always spans whole segments, so it can never
start or end mid-sentence. Rules (in priority order):
1. speaker change → new segment
2. sentence-final punctuation (. ? ! …) → end segment
3. pause longer than PAUSE_SPLIT_SECONDS → end segment (speech without punctuation)
4. MAX_WORDS_PER_SEGMENT safety cap (run-on speech)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from clipmaker.providers.transcription.base import Word

PAUSE_SPLIT_SECONDS = 1.2
MAX_WORDS_PER_SEGMENT = 45
_SENTENCE_END = (".", "?", "!", "…", '."', '?"', '!"')


@dataclass(slots=True)
class Segment:
    """A sentence-like unit of speech."""

    idx: int
    start: float
    end: float
    speaker: str | None
    words: list[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


def build_segments(words: list[Word]) -> list[Segment]:
    """Group words into segments (pure function)."""
    segments: list[Segment] = []
    current: list[Word] = []

    def flush() -> None:
        if current:
            segments.append(
                Segment(
                    idx=len(segments),
                    start=current[0].start,
                    end=current[-1].end,
                    speaker=current[0].speaker,
                    words=list(current),
                )
            )
            current.clear()

    for word in words:
        if current:
            prev = current[-1]
            if word.speaker != prev.speaker or word.start - prev.end > PAUSE_SPLIT_SECONDS:
                flush()
        current.append(word)
        if word.text.endswith(_SENTENCE_END) or len(current) >= MAX_WORDS_PER_SEGMENT:
            flush()
    flush()
    return segments


def _clock(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(int(m), 60)
    return f"{h}:{m:02d}:{s:04.1f}" if h else f"{m:02d}:{s:04.1f}"


def render_for_llm(segments: list[Segment]) -> str:
    """Numbered, timestamped, speaker-labelled transcript. Deterministic (cache-friendly)."""
    lines = [
        f"[S{seg.idx} | {_clock(seg.start)}-{_clock(seg.end)} | "
        f"{seg.speaker or 'Speaker'}] {seg.text}"
        for seg in segments
    ]
    return "\n".join(lines)
