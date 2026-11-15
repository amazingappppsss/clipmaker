"""AssemblyAI implementation of TranscriptionProvider (REST, via httpx).

Flow: upload audio → create transcript job (speaker labels on) → poll until done.
Long recordings are handled by the provider; we never chunk, so no words are duplicated or lost
at chunk seams. Cost is estimated from duration x configured hourly price.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from clipmaker.core.config import Settings
from clipmaker.providers.transcription.base import (
    Heartbeat,
    TranscriptionError,
    TranscriptionResult,
    Word,
)

POLL_INTERVAL_SECONDS = 2.0  # short audio finishes in seconds; poll often
_UPLOAD_CHUNK = 5 * 1024 * 1024


def _iter_file(path: Path) -> Iterator[bytes]:
    with path.open("rb") as fh:
        while chunk := fh.read(_UPLOAD_CHUNK):
            yield chunk


def parse_transcript(payload: dict[str, Any]) -> tuple[list[Word], bool]:
    """Convert AssemblyAI's word list (milliseconds) to Words (seconds). Pure; unit-tested."""
    words: list[Word] = []
    has_speakers = False
    for w in payload.get("words") or []:
        text = str(w.get("text", "")).strip()
        if not text:
            continue
        speaker = w.get("speaker")
        has_speakers = has_speakers or speaker is not None
        words.append(
            Word(
                text=text,
                start=float(w["start"]) / 1000.0,
                end=float(w["end"]) / 1000.0,
                confidence=float(w.get("confidence") or 0.0),
                speaker=f"Speaker {speaker}" if speaker is not None else None,
            )
        )
    return words, has_speakers


class AssemblyAIProvider:
    """TranscriptionProvider backed by AssemblyAI."""

    name = "assemblyai"

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if client is None:
            # A blank env var counts as missing, so the error says "not configured".
            if (
                not settings.assemblyai_api_key
                or not settings.assemblyai_api_key.get_secret_value()
            ):
                raise TranscriptionError("ASSEMBLYAI_API_KEY is not configured", retryable=False)
            client = httpx.Client(
                base_url=settings.assemblyai_base_url,
                headers={"authorization": settings.assemblyai_api_key.get_secret_value()},
                timeout=httpx.Timeout(120.0, connect=15.0),
            )
        self._client = client
        self._settings = settings
        self._sleep = sleep

    def _check(self, response: httpx.Response, what: str) -> dict[str, Any]:
        if response.status_code in (401, 403):
            raise TranscriptionError("AssemblyAI API key is invalid", retryable=False)
        if response.status_code == 429 or response.status_code >= 500:
            raise TranscriptionError(
                f"AssemblyAI {what} failed ({response.status_code})", retryable=True
            )
        if response.status_code >= 400:
            raise TranscriptionError(
                f"AssemblyAI {what} rejected: {response.text[:300]}", retryable=False
            )
        body: dict[str, Any] = response.json()
        return body

    def transcribe(
        self, audio: Path | str, language: str | None, heartbeat: Heartbeat
    ) -> TranscriptionResult:
        try:
            # A URL is fetched by AssemblyAI directly: no audio track to extract, and no
            # upload of our own, which is the slowest part of preparing a video.
            if isinstance(audio, str):
                source = audio
            else:
                source = self._check(
                    self._client.post(
                        "/v2/upload",
                        content=_iter_file(audio),
                        headers={"content-type": "application/octet-stream"},
                    ),
                    "upload",
                )["upload_url"]
            request: dict[str, Any] = {
                "audio_url": source,
                "speaker_labels": True,
                "punctuate": True,
                "format_text": True,
            }
            if language:
                request["language_code"] = language
            else:
                request["language_detection"] = True
            job = self._check(self._client.post("/v2/transcript", json=request), "submit")

            deadline = time.monotonic() + self._settings.transcription_timeout_seconds
            while job.get("status") not in ("completed", "error"):
                if time.monotonic() > deadline:
                    raise TranscriptionError("Transcription timed out", retryable=True)
                heartbeat()
                self._sleep(POLL_INTERVAL_SECONDS)
                job = self._check(self._client.get(f"/v2/transcript/{job['id']}"), "poll")
        except httpx.HTTPError as exc:
            raise TranscriptionError(
                f"Network error talking to AssemblyAI: {exc}", retryable=True
            ) from exc

        if job["status"] == "error":
            # Provider-side errors are usually about the audio itself (unsupported, silent).
            raise TranscriptionError(f"Transcription failed: {job.get('error')}", retryable=False)

        words, has_speakers = parse_transcript(job)
        duration = float(job.get("audio_duration") or (words[-1].end if words else 0.0))
        cost = (
            Decimal(str(duration))
            / Decimal(3600)
            * Decimal(str(self._settings.assemblyai_usd_per_hour))
        )
        return TranscriptionResult(
            words=words,
            language=job.get("language_code") or language,
            duration_seconds=duration,
            provider=self.name,
            model=str(job.get("speech_model") or "default"),
            cost_usd=cost.quantize(Decimal("0.000001")),
            has_speakers=has_speakers,
            raw={k: v for k, v in job.items() if k not in ("words", "utterances")},
        )
