from __future__ import annotations

from typing import Any

from src.Infrastructure.External.Observability.langfuse.langfuse_tracer import LangfuseTracer
from src.Infrastructure.External.Observability.langfuse.null_tracer import NullTraceHandle


class _FakeGeneration:
    def __init__(self) -> None:
        self.update_calls: list[dict[str, Any]] = []
        self.end_calls: int = 0

    def update(self, **kwargs: Any) -> None:
        self.update_calls.append(kwargs)

    def end(self) -> None:
        self.end_calls += 1


class _ErrorGeneration:
    def update(self, **kwargs: Any) -> None:
        raise RuntimeError("Langfuse update failed")

    def end(self) -> None:
        raise RuntimeError("Langfuse end failed")


class _FakeLangfuseClient:
    def __init__(self, generation: Any = None) -> None:
        self.start_observation_calls: list[dict[str, Any]] = []
        self._generation = generation if generation is not None else _FakeGeneration()

    def start_observation(self, **kwargs: Any) -> Any:
        self.start_observation_calls.append(kwargs)
        return self._generation


class _ErrorLangfuseClient:
    def start_observation(self, **kwargs: Any) -> Any:
        raise RuntimeError("Langfuse unreachable")


def _messages() -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Extract the profile."},
    ]


def _start(client: Any, **overrides: Any) -> Any:
    defaults = {
        "name": "extract_profile_from_cv",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "prompt_version": "v1",
        "system_prompt": None,
        "messages": [],
    }
    defaults.update(overrides)
    return LangfuseTracer(client=client, environment="development").start_completion(**defaults)


# --- start_completion / metadata ---


def test_start_completion_sends_correct_metadata_and_input() -> None:
    client = _FakeLangfuseClient()

    _start(
        client,
        name="extract_profile_from_cv",
        model="llama-3.3-70b-versatile",
        system_prompt="You are a helpful assistant.",
        messages=_messages(),
    )

    assert len(client.start_observation_calls) == 1
    call = client.start_observation_calls[0]
    assert call["as_type"] == "generation"
    assert call["name"] == "extract_profile_from_cv"
    assert call["model"] == "llama-3.3-70b-versatile"
    assert call["input"] == _messages()
    assert call["metadata"] == {
        "provider": "groq",
        "prompt_version": "v1",
        "system_prompt": "You are a helpful assistant.",
        "environment": "development",
        "source": "mission-radar-ai",
    }


def test_start_completion_with_none_system_prompt() -> None:
    client = _FakeLangfuseClient()

    _start(client, system_prompt=None)

    assert client.start_observation_calls[0]["metadata"]["system_prompt"] is None


def test_start_completion_swallows_sdk_exception_and_returns_null_handle() -> None:
    handle = _start(_ErrorLangfuseClient())

    assert isinstance(handle, NullTraceHandle)
    handle.succeed(output="ok", input_tokens=None, output_tokens=None, total_tokens=None)
    handle.fail(error=RuntimeError("boom"))


# --- succeed() ---


def test_succeed_updates_output_and_usage_and_ends() -> None:
    generation = _FakeGeneration()
    handle = _start(_FakeLangfuseClient(generation=generation))

    handle.succeed(output="hello world", input_tokens=10, output_tokens=5, total_tokens=15)

    assert generation.update_calls == [
        {
            "output": "hello world",
            "usage_details": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    ]
    assert generation.end_calls == 1


def test_succeed_with_missing_token_counts_omits_usage_details() -> None:
    generation = _FakeGeneration()
    handle = _start(_FakeLangfuseClient(generation=generation))

    handle.succeed(output="hello", input_tokens=None, output_tokens=None, total_tokens=None)

    assert generation.update_calls == [{"output": "hello", "usage_details": None}]
    assert generation.end_calls == 1


def test_succeed_swallows_sdk_exception() -> None:
    handle = _start(_FakeLangfuseClient(generation=_ErrorGeneration()))

    handle.succeed(output="hello", input_tokens=1, output_tokens=1, total_tokens=2)


# --- fail() ---


def test_fail_sends_error_level_and_status_message_and_ends() -> None:
    generation = _FakeGeneration()
    handle = _start(_FakeLangfuseClient(generation=generation))

    handle.fail(error=RuntimeError("Groq timeout"))

    assert generation.update_calls == [{"level": "ERROR", "status_message": "Groq timeout"}]
    assert generation.end_calls == 1


def test_fail_swallows_sdk_exception() -> None:
    handle = _start(_FakeLangfuseClient(generation=_ErrorGeneration()))

    handle.fail(error=RuntimeError("boom"))
