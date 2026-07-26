from __future__ import annotations

from typing import Any

import pytest

from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Observability.langfuse import factory as factory_module
from src.Infrastructure.External.Observability.langfuse.langfuse_tracer import LangfuseTracer
from src.Infrastructure.External.Observability.langfuse.null_tracer import NullTracer


class _FakeLangfuse:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class _RaisingLangfuse:
    def __init__(self, **kwargs: Any) -> None:
        raise RuntimeError("bad Langfuse config")


@pytest.fixture(autouse=True)
def _reset_cache_and_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    factory_module.get_langfuse_tracer.cache_clear()
    monkeypatch.setattr(settings, "LANGFUSE_ENABLED", False)
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setattr(settings, "LANGFUSE_HOST", "https://example.invalid")
    yield
    factory_module.get_langfuse_tracer.cache_clear()


def test_returns_null_tracer_when_disabled() -> None:
    tracer = factory_module.get_langfuse_tracer()

    assert isinstance(tracer, NullTracer)


def test_returns_langfuse_tracer_when_enabled_and_valid_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LANGFUSE_ENABLED", True)
    monkeypatch.setattr(factory_module, "Langfuse", _FakeLangfuse)

    tracer = factory_module.get_langfuse_tracer()

    assert isinstance(tracer, LangfuseTracer)


def test_falls_back_to_null_tracer_when_langfuse_init_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LANGFUSE_ENABLED", True)
    monkeypatch.setattr(factory_module, "Langfuse", _RaisingLangfuse)

    tracer = factory_module.get_langfuse_tracer()

    assert isinstance(tracer, NullTracer)


def test_result_is_cached() -> None:
    first = factory_module.get_langfuse_tracer()
    second = factory_module.get_langfuse_tracer()

    assert first is second
