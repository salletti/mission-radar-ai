from __future__ import annotations

from typing import Protocol


class LLMTraceHandle(Protocol):
    """Handle for a single in-flight LLM call trace, returned by LLMTracer.start_completion.

    Started before the LLM call, resolved with succeed() or fail() right after —
    this mirrors the underlying tracing SDK's span lifecycle so call latency is
    measured accurately, without leaking that lifecycle outside Infrastructure/.
    """

    def succeed(
        self,
        *,
        output: str,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int | None,
    ) -> None: ...

    def fail(self, *, error: Exception) -> None: ...


class LLMTracer(Protocol):
    """Traces LLM calls made by an LLMGateway implementation (e.g. GroqLLMGateway).

    Deliberately named LLMTracer rather than a generic "Tracer": the project may
    add other observability targets later (OpenTelemetry, Datadog...) and this
    Protocol is scoped specifically to LLM call tracing.
    """

    def start_completion(
        self,
        *,
        name: str,
        provider: str,
        model: str,
        prompt_version: str,
        system_prompt: str | None,
        messages: list[dict[str, str]],
    ) -> LLMTraceHandle: ...
