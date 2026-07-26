"""Tests for build_default_judge_model — no real network, no API key.

LocalModel's constructor only stores configuration (verified against the
installed deepeval source: no HTTP client is built until generate()/
a_generate() is actually called), so these tests never touch the network.
"""
from deepeval.models import LocalModel

from integrations.deepeval import config
from integrations.deepeval.judge_model import build_default_judge_model


def test_returns_a_local_model() -> None:
    model = build_default_judge_model(api_key="fake-key")
    assert isinstance(model, LocalModel)


def test_uses_configured_model_name() -> None:
    model = build_default_judge_model(api_key="fake-key")
    assert model.name == config.JUDGE_MODEL_NAME


def test_uses_configured_base_url() -> None:
    model = build_default_judge_model(api_key="fake-key")
    assert model.base_url == config.JUDGE_MODEL_BASE_URL


def test_uses_configured_temperature() -> None:
    model = build_default_judge_model(api_key="fake-key")
    assert model.temperature == config.JUDGE_MODEL_TEMPERATURE


def test_uses_the_given_api_key() -> None:
    model = build_default_judge_model(api_key="my-secret-key")
    assert model.local_model_api_key.get_secret_value() == "my-secret-key"
