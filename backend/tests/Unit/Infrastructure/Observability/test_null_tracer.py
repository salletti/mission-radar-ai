from __future__ import annotations

from src.Infrastructure.External.Observability.langfuse.null_tracer import NullTracer


def test_start_completion_returns_a_handle() -> None:
    tracer = NullTracer()

    handle = tracer.start_completion(
        name="analyze_post",
        provider="groq",
        model="llama-3.3-70b-versatile",
        prompt_version="v1",
        system_prompt=None,
        messages=[{"role": "user", "content": "hi"}],
    )

    assert handle is not None


def test_handle_succeed_is_noop() -> None:
    handle = NullTracer().start_completion(
        name="x", provider="groq", model="m", prompt_version="v1", system_prompt=None, messages=[]
    )

    result = handle.succeed(output="ok", input_tokens=1, output_tokens=2, total_tokens=3)

    assert result is None


def test_handle_fail_is_noop() -> None:
    handle = NullTracer().start_completion(
        name="x", provider="groq", model="m", prompt_version="v1", system_prompt=None, messages=[]
    )

    result = handle.fail(error=RuntimeError("boom"))

    assert result is None
