from __future__ import annotations

import logging
from typing import Any

from src.Infrastructure.External.Observability.langfuse.null_tracer import NullTraceHandle

logger = logging.getLogger(__name__)


def _build_usage_details(
    *, input_tokens: int | None, output_tokens: int | None, total_tokens: int | None
) -> dict[str, int] | None:
    usage_details = {
        key: value
        for key, value in (
            ("prompt_tokens", input_tokens),
            ("completion_tokens", output_tokens),
            ("total_tokens", total_tokens),
        )
        if value is not None
    }
    return usage_details or None


class _LangfuseTraceHandle:
    """Wraps a live Langfuse generation span. Never raises — SDK errors are logged and swallowed."""

    def __init__(self, generation: Any) -> None:
        self._generation = generation

    def succeed(
        self,
        *,
        output: str,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int | None,
    ) -> None:
        try:
            self._generation.update(
                output=output,
                usage_details=_build_usage_details(
                    input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens
                ),
            )
            self._generation.end()
        except Exception as e:
            logger.warning("Langfuse trace succeed() failed: %s", e)

    def fail(self, *, error: Exception) -> None:
        try:
            self._generation.update(level="ERROR", status_message=str(error))
            self._generation.end()
        except Exception as e:
            logger.warning("Langfuse trace fail() failed: %s", e)


class LangfuseTracer:
    """Real LLMTracer implementation backed by the Langfuse SDK.

    Every method is best-effort: SDK errors are logged and swallowed, never raised,
    so a Langfuse outage or misconfiguration can never break an LLM call. Network
    failures during export are already handled asynchronously by the SDK's own
    background batching, but the try/except here also covers synchronous failures
    (e.g. non-serializable trace input).
    """

    def __init__(self, client: Any, *, environment: str, source: str = "mission-radar-ai") -> None:
        self._client = client
        self._environment = environment
        self._source = source

    def start_completion(
        self,
        *,
        name: str,
        provider: str,
        model: str,
        prompt_version: str,
        system_prompt: str | None,
        messages: list[dict[str, str]],
    ) -> _LangfuseTraceHandle | NullTraceHandle:
        try:
            generation = self._client.start_observation(
                as_type="generation",
                name=name,
                model=model,
                input=messages,
                metadata={
                    "provider": provider,
                    "prompt_version": prompt_version,
                    "system_prompt": system_prompt,
                    "environment": self._environment,
                    "source": self._source,
                },
            )
            return _LangfuseTraceHandle(generation)
        except Exception as e:
            logger.warning("Langfuse start_completion() failed: %s", e)
            return NullTraceHandle()
