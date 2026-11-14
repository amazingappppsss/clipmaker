"""Deterministic stand-ins for paid providers, so pipeline tests cost nothing.

They implement the same Protocols as the real providers (TranscriptionProvider / LLMProvider)
and can be told to fail, so retry and failure paths are exercised for real.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from clipmaker.pipeline.prompts import ANALYSIS_SCHEMA, CANDIDATES_SCHEMA, METADATA_SCHEMA
from clipmaker.providers.llm.base import LLMError, LLMRequest, LLMResult, LLMUsage
from clipmaker.providers.transcription.base import (
    TranscriptionError,
    TranscriptionResult,
    Word,
)

# A two-speaker conversation; each entry becomes one sentence. Repeated to ~8 minutes.
_SCRIPT = [
    ("A", "Welcome back to the show, today we are talking about building habits that stick."),
    ("B", "Thanks for having me, this is a topic I have thought about for ten years."),
    ("A", "So what was the moment everything changed for you?"),
    ("B", "I stopped checking my phone first thing in the morning and everything changed."),
    ("B", "For a month I wrote one page every morning before touching any screen."),
    ("B", "By the end of that month I had finished the first draft of my book."),
    ("A", "That is incredible, why do you think it worked so well?"),
    ("B", "Because the first hour sets the tone and attention is the real currency."),
    ("A", "Most people say they do not have time, what do you tell them?"),
    ("B", "You do not need more time, you need fewer inputs before you create."),
    ("B", "Start with ten minutes, protect them like a meeting with your future self."),
    ("A", "Let us talk about failure, did you ever quit?"),
    ("B", "I almost quit after the first rejection letter, honestly I cried that night."),
    ("B", "Then one email from a reader changed my mind about everything."),
    ("B", "She said my blog post stopped her from giving up on her own dream."),
    ("A", "Wow, that is a powerful reason to keep going."),
]


def fake_words(repeats: int = 6, words_per_second: float = 2.6) -> list[Word]:
    """Timed words for the script; ~0.5s pause between sentences, 1.5s between speakers."""
    words: list[Word] = []
    t = 0.5
    prev_speaker = None
    for _ in range(repeats):
        for speaker, sentence in _SCRIPT:
            if prev_speaker is not None:
                t += 1.5 if speaker != prev_speaker else 0.5
            for token in sentence.split():
                dur = 1.0 / words_per_second
                words.append(
                    Word(
                        text=token,
                        start=round(t, 3),
                        end=round(t + dur * 0.9, 3),
                        confidence=0.97,
                        speaker=f"Speaker {speaker}",
                    )
                )
                t += dur
            prev_speaker = speaker
    return words


class FakeTranscriber:
    """TranscriptionProvider fake. `fail_times` failures (retryable or not) before succeeding."""

    name = "fake"

    def __init__(
        self, fail_times: int = 0, retryable: bool = True, words: list[Word] | None = None
    ) -> None:
        self.calls = 0
        self.fail_times = fail_times
        self.retryable = retryable
        self.words = fake_words() if words is None else words

    def transcribe(
        self, audio: Path, language: str | None, heartbeat: Callable[[], None]
    ) -> TranscriptionResult:
        self.calls += 1
        assert audio.is_file(), "pipeline must hand the provider a real audio file"
        heartbeat()
        if self.calls <= self.fail_times:
            raise TranscriptionError("simulated provider outage", retryable=self.retryable)
        return TranscriptionResult(
            words=self.words,
            language=language or "en",
            duration_seconds=self.words[-1].end if self.words else 0.0,
            provider=self.name,
            model="fake-1",
            cost_usd=Decimal("0.010000"),
            has_speakers=True,
            raw={"id": "fake"},
        )


_SEG_LINE = re.compile(r"^\[S(\d+) \|", re.MULTILINE)


class FakeLLM:
    """LLMProvider fake that answers each schema plausibly from the given context."""

    name = "fake"

    def __init__(self, fail_with: LLMError | None = None) -> None:
        self.requests: list[LLMRequest] = []
        self.fail_with = fail_with

    def complete_json(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        if self.fail_with is not None:
            raise self.fail_with
        if request.schema is ANALYSIS_SCHEMA:
            data = self._analysis(request.context)
        elif request.schema is CANDIDATES_SCHEMA:
            data = self._candidates(request.context)
        elif request.schema is METADATA_SCHEMA:
            data = self._metadata(request.context)
        else:  # pragma: no cover - guards against unknown schemas
            raise AssertionError("unexpected schema")
        usage = LLMUsage(input_tokens=1000, output_tokens=200)
        return LLMResult(
            data=data, model=f"fake-{request.tier}", usage=usage, cost_usd=Decimal("0.002")
        )

    @staticmethod
    def _indexes(context: str) -> list[int]:
        return [int(m) for m in _SEG_LINE.findall(context)]

    def _analysis(self, context: str) -> dict[str, Any]:
        idx = self._indexes(context)
        return {
            "summary": "A conversation about habits, focus and not giving up.",
            "content_type": "podcast",
            "speakers": [
                {"label": "Speaker A", "role": "host", "description": "asks questions"},
                {"label": "Speaker B", "role": "guest", "description": "author"},
            ],
            "topics": ["habits", "focus", "failure"],
            "sections": [
                {
                    "title": "Intro",
                    "start_segment": idx[0],
                    "end_segment": idx[-1],
                    "summary": "All",
                }
            ],
            "notable_moments": [
                {
                    "start_segment": idx[3],
                    "end_segment": idx[5],
                    "kind": "story",
                    "why": "turning point",
                }
            ],
        }

    def _candidates(self, context: str) -> dict[str, Any]:
        idx = self._indexes(context)
        n = len(_SCRIPT)
        cands = []
        # One strong story per script repetition, plus a weak one and a duplicate.
        for rep, base in enumerate(range(0, len(idx) - n + 1, n)):
            strength = 9.0 - rep * 0.5
            cands.append(
                {
                    "start_segment": idx[base + 2],
                    "end_segment": idx[base + 7],
                    "category": "story",
                    "rationale": "habit turning point",
                    "hook_line": "I stopped checking my phone first thing in the morning.",
                    "five_second_moment": "That's when I realized the phone was running my day.",
                    "before_state": "anxious",
                    "after_state": "in control",
                    "missing_context": "",
                    "scores": {
                        s: strength
                        for s in (
                            "hook",
                            "curiosity_gap",
                            "stakes",
                            "specificity",
                            "momentum",
                            "emotion",
                            "transformation",
                            "causality",
                            "payoff",
                            "share_trigger",
                            "standalone",
                        )
                    },
                }
            )
        cands.append({**cands[0], "rationale": "duplicate of first"})
        cands.append(
            {
                "start_segment": idx[11],
                "end_segment": idx[11],
                "category": "story",
                "rationale": "too short",
                "hook_line": "x",
                "scores": {s: 2.0 for s in cands[0]["scores"]},
            }
        )
        return {"candidates": cands}

    def _metadata(self, context: str) -> dict[str, Any]:
        count = len(re.findall(r"^Clip \d+", context, re.MULTILINE))
        return {
            "clips": [
                {
                    "clip_number": i + 1,
                    "title": f"The phone habit #{i + 1}",
                    "hook": "One morning change finished a whole book.",
                    "alt_titles": ["A", "B", "C"],
                    "social_caption": "Try this tomorrow.",
                    "hashtags": ["#habits", "#focus", "#writing"],
                }
                for i in range(count)
            ]
        }
