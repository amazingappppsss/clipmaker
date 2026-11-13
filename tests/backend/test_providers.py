"""AssemblyAI and Anthropic providers against simulated transports — no network, no cost."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from clipmaker.core.config import get_settings
from clipmaker.pipeline.prompts import ANALYSIS_SCHEMA
from clipmaker.providers.llm.anthropic_provider import FALLBACK_BETA, AnthropicProvider
from clipmaker.providers.llm.base import LLMError, LLMRequest, LLMUsage
from clipmaker.providers.llm.pricing import cost_for
from clipmaker.providers.transcription.assemblyai import AssemblyAIProvider, parse_transcript
from clipmaker.providers.transcription.base import TranscriptionError


# --- AssemblyAI -------------------------------------------------------------------------
def _assembly(handler: Any) -> AssemblyAIProvider:
    client = httpx.Client(
        base_url="https://api.assemblyai.test", transport=httpx.MockTransport(handler)
    )
    return AssemblyAIProvider(get_settings(), client=client, sleep=lambda _: None)


@pytest.fixture
def audio(tmp_path: Path) -> Path:
    path = tmp_path / "a.mp3"
    path.write_bytes(b"ID3" + b"\0" * 1000)
    return path


def test_assemblyai_happy_path(audio: Path) -> None:
    calls: list[str] = []
    polls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(f"{req.method} {req.url.path}")
        if req.url.path == "/v2/upload":
            assert req.read() == audio.read_bytes()
            return httpx.Response(200, json={"upload_url": "https://cdn/x"})
        if req.method == "POST":
            body = json.loads(req.content)
            assert body["speaker_labels"] is True and body["language_code"] == "en"
            return httpx.Response(200, json={"id": "t1", "status": "queued"})
        polls["n"] += 1
        if polls["n"] < 2:
            return httpx.Response(200, json={"id": "t1", "status": "processing"})
        return httpx.Response(
            200,
            json={
                "id": "t1",
                "status": "completed",
                "language_code": "en",
                "audio_duration": 3.0,
                "words": [
                    {"text": "Hello", "start": 100, "end": 400, "confidence": 0.9, "speaker": "A"},
                    {"text": "world.", "start": 450, "end": 900, "confidence": 0.8, "speaker": "A"},
                ],
            },
        )

    beats: list[int] = []
    result = _assembly(handler).transcribe(audio, "en", lambda: beats.append(1))
    assert [w.text for w in result.words] == ["Hello", "world."]
    assert result.words[0].start == pytest.approx(0.1) and result.words[0].speaker == "Speaker A"
    assert result.has_speakers and beats
    assert result.cost_usd == Decimal("0.000125")  # 3s at $0.15/h
    assert calls[0] == "POST /v2/upload"


@pytest.mark.parametrize(
    ("status", "retryable"), [(401, False), (400, False), (429, True), (503, True)]
)
def test_assemblyai_http_errors(audio: Path, status: int, retryable: bool) -> None:
    provider = _assembly(lambda req: httpx.Response(status, json={"error": "x"}))
    with pytest.raises(TranscriptionError) as err:
        provider.transcribe(audio, None, lambda: None)
    assert err.value.retryable is retryable


def test_assemblyai_job_error_is_permanent(audio: Path) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/v2/upload":
            return httpx.Response(200, json={"upload_url": "u"})
        return httpx.Response(200, json={"id": "t", "status": "error", "error": "no audio"})

    with pytest.raises(TranscriptionError) as err:
        _assembly(handler).transcribe(audio, None, lambda: None)
    assert err.value.retryable is False


def test_assemblyai_network_error_is_retryable(audio: Path) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(TranscriptionError) as err:
        _assembly(handler).transcribe(audio, None, lambda: None)
    assert err.value.retryable is True


def test_parse_transcript_skips_empty_words() -> None:
    words, speakers = parse_transcript({"words": [{"text": " ", "start": 0, "end": 1}]})
    assert words == [] and speakers is False


# --- Anthropic --------------------------------------------------------------------------
class _FakeMessages:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.kwargs: dict[str, Any] = {}
        self.response = response
        self.error = error

    def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def _response(text: str, stop: str = "end_turn", model: str = "claude-opus-5-5") -> Any:
    return SimpleNamespace(
        model=model,
        stop_reason=stop,
        _request_id="req_1",
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
        usage=SimpleNamespace(
            input_tokens=1000,
            output_tokens=500,
            cache_read_input_tokens=20000,
            cache_creation_input_tokens=0,
        ),
    )


def _provider(
    response: Any = None, error: Exception | None = None
) -> tuple[AnthropicProvider, Any]:
    fake = SimpleNamespace(messages=_FakeMessages(response, error))
    fake.beta = SimpleNamespace(messages=fake.messages)
    return AnthropicProvider(get_settings(), client=fake), fake.messages  # type: ignore[arg-type]


def _req(tier: str = "smart") -> LLMRequest:
    return LLMRequest(
        tier=tier,
        system="SYS",
        context="TRANSCRIPT",
        instruction="Do it",  # type: ignore[arg-type]
        schema=ANALYSIS_SCHEMA,
    )


def test_anthropic_request_shape_and_cost() -> None:
    provider, messages = _provider(_response('{"summary": "ok"}'))
    result = provider.complete_json(_req())
    kw = messages.kwargs
    assert kw["model"] == "claude-opus-5-5"
    assert kw["system"][1] == {
        "type": "text",
        "text": "TRANSCRIPT",
        "cache_control": {"type": "ephemeral"},
    }
    assert kw["output_config"]["format"] == {"type": "json_schema", "schema": ANALYSIS_SCHEMA}
    assert kw["output_config"]["effort"] == "high"
    assert kw["betas"] == [FALLBACK_BETA] and kw["fallbacks"] == "default"
    assert "thinking" not in kw and "temperature" not in kw
    assert result.data == {"summary": "ok"}
    # 1000 in * $4 + 20000 cache-read * $0.4 + 500 out * $20, per million
    assert result.cost_usd == Decimal("0.022000")


def test_anthropic_fast_tier_uses_haiku_without_fallback() -> None:
    provider, messages = _provider(_response("{}", model="claude-haiku-5-5"))
    provider.complete_json(_req("fast"))
    assert messages.kwargs["model"] == "claude-haiku-5-5"
    assert "fallbacks" not in messages.kwargs


@pytest.mark.parametrize(
    ("response", "retryable"),
    [
        (_response("{}", stop="refusal"), False),
        (_response("{", stop="end_turn"), True),
        (_response("{}", stop="max_tokens"), True),
        (_response("[1]"), True),
    ],
)
def test_anthropic_bad_outputs(response: Any, retryable: bool) -> None:
    provider, _ = _provider(response)
    with pytest.raises(LLMError) as err:
        provider.complete_json(_req())
    assert err.value.retryable is retryable


def test_anthropic_missing_key_is_permanent() -> None:
    with pytest.raises(LLMError, match="not configured") as err:
        AnthropicProvider(get_settings())  # ANTHROPIC_API_KEY="" in tests
    assert err.value.retryable is False


def test_assemblyai_missing_key_is_permanent() -> None:
    with pytest.raises(TranscriptionError, match="not configured") as err:
        AssemblyAIProvider(get_settings())
    assert err.value.retryable is False


def test_fallback_model_noted() -> None:
    provider, _ = _provider(_response("{}", model="claude-opus-5"))
    assert provider.complete_json(_req()).notes == ["served by fallback model claude-opus-5"]


def test_unknown_model_priced_conservatively() -> None:
    assert cost_for("mystery", LLMUsage(input_tokens=1_000_000)) == Decimal("10.000000")
