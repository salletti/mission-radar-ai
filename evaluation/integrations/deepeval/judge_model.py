"""Judge-model factory for DeepEval — one of two files in evaluation/ allowed
to import the `deepeval` package directly (see deepeval_adapter.py for the other).
"""
from __future__ import annotations

from deepeval.models import LocalModel

from integrations.deepeval import config


def build_default_judge_model(api_key: str) -> LocalModel:
    """Build the default LLM-as-a-judge model for DeepEval metrics.

    Groq exposes an OpenAI-compatible endpoint, so DeepEval's own LocalModel
    (its official class for any OpenAI-compatible API — vLLM, LM Studio,
    Ollama, ...) can talk to it directly. No custom DeepEvalBaseLLM subclass
    is needed: reusing DeepEval's own integration is preferred over
    maintaining a hand-written wrapper around the Groq SDK.
    """
    return LocalModel(
        model=config.JUDGE_MODEL_NAME,
        base_url=config.JUDGE_MODEL_BASE_URL,
        api_key=api_key,
        temperature=config.JUDGE_MODEL_TEMPERATURE,
    )
