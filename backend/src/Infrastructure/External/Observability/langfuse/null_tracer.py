from __future__ import annotations


class NullTraceHandle:
    """No-op handle — also used by LangfuseTracer as a fallback when the SDK errors."""

    def succeed(self, **kwargs: object) -> None:
        return None

    def fail(self, **kwargs: object) -> None:
        return None


class NullTracer:
    """No-op LLMTracer used when Langfuse is disabled or fails to initialize.

    Makes "disabled = zero behavioral impact" true by construction rather than
    via `if enabled:` checks scattered through GroqLLMGateway.
    """

    def start_completion(self, **kwargs: object) -> NullTraceHandle:
        return NullTraceHandle()
