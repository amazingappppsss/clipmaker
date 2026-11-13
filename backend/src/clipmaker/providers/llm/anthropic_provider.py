"""Claude (Anthropic API) implementation of LLMProvider.

* Structured outputs (`output_config.format` json_schema) — the response is guaranteed JSON
  matching the schema; we still validate with json.loads.
* Prompt caching — system prompt + video context are a cached prefix, so the analysis and
  selection calls for one video pay full price for the transcript only once.
* Adaptive thinking is always on for current models; depth is set with `effort`.
* Server-side refusal fallback (beta) on the smart model, enabled by default.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from clipmaker.core.config import Settings
from clipmaker.providers.llm.base import LLMError, LLMRequest, LLMResult, LLMUsage
from clipmaker.providers.llm.pricing import cost_for

logger = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    """LLMProvider backed by the Anthropic Messages API."""

    name = "anthropic"

    def __init__(self, settings: Settings, client: anthropic.Anthropic | None = None) -> None:
        if client is None:
            # A blank env var counts as missing, so the error says "not configured".
            if not settings.anthropic_api_key or not settings.anthropic_api_key.get_secret_value():
                raise LLMError("ANTHROPIC_API_KEY is not configured", retryable=False)
            client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key.get_secret_value(), max_retries=3
            )
        self._client = client
        self._settings = settings

    def _model_and_effort(self, tier: str) -> tuple[str, str]:
        s = self._settings
        return (
            (s.llm_smart_model, s.llm_smart_effort)
            if tier == "smart"
            else (s.llm_fast_model, s.llm_fast_effort)
        )

    def complete_json(self, request: LLMRequest) -> LLMResult:
        model, effort = self._model_and_effort(request.tier)
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens,
            "system": [
                {"type": "text", "text": request.system},
                # Stable per-video context, cached across this video's calls.
                {
                    "type": "text",
                    "text": request.context,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            "messages": [{"role": "user", "content": request.instruction}],
            "output_config": {
                "effort": effort,
                "format": {"type": "json_schema", "schema": request.schema},
            },
        }
        use_fallback = request.tier == "smart" and self._settings.llm_refusal_fallback
        if use_fallback:
            params["betas"] = [FALLBACK_BETA]
            params["fallbacks"] = "default"

        try:
            response: Any = (
                self._client.beta.messages.create(**params)
                if use_fallback
                else self._client.messages.create(**params)
            )
        except anthropic.AuthenticationError as exc:
            raise LLMError("Anthropic API key is invalid", retryable=False) from exc
        except anthropic.PermissionDeniedError as exc:
            raise LLMError("Anthropic API key lacks permission", retryable=False) from exc
        except anthropic.BadRequestError as exc:
            raise LLMError(
                f"Anthropic rejected the request: {exc.message}", retryable=False
            ) from exc
        except anthropic.NotFoundError as exc:
            raise LLMError(f"Unknown model or endpoint: {exc.message}", retryable=False) from exc
        except anthropic.RateLimitError as exc:
            raise LLMError("Anthropic rate limit reached", retryable=True) from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(
                f"Anthropic error {exc.status_code}", retryable=exc.status_code >= 500
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Could not reach the Anthropic API", retryable=True) from exc

        served_by = str(getattr(response, "model", model))
        raw_usage = response.usage
        usage = LLMUsage(
            input_tokens=int(raw_usage.input_tokens or 0),
            output_tokens=int(raw_usage.output_tokens or 0),
            cache_read_tokens=int(getattr(raw_usage, "cache_read_input_tokens", 0) or 0),
            cache_write_tokens=int(getattr(raw_usage, "cache_creation_input_tokens", 0) or 0),
        )
        request_id = getattr(response, "_request_id", None)
        notes = [] if served_by == model else [f"served by fallback model {served_by}"]

        if response.stop_reason == "refusal":
            raise LLMError("The model declined this content", retryable=False)
        if response.stop_reason == "max_tokens":
            raise LLMError("Model output was cut off (max_tokens)", retryable=True)

        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise LLMError("Model returned no text output", retryable=True)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError("Model returned invalid JSON", retryable=True) from exc
        if not isinstance(data, dict):
            raise LLMError("Model JSON was not an object", retryable=True)

        cost = cost_for(served_by, usage)
        logger.info(
            "llm_call",
            extra={
                "model": served_by,
                "tier": request.tier,
                "request_id": request_id,
                "input": usage.input_tokens,
                "output": usage.output_tokens,
                "cache_read": usage.cache_read_tokens,
                "cost_usd": str(cost),
            },
        )
        return LLMResult(
            data=data,
            model=served_by,
            usage=usage,
            cost_usd=cost,
            request_id=request_id,
            notes=notes,
        )
