"""Tunable configuration for the DeepEval integration.

Centralized here so metric thresholds and judge-model settings can be
adjusted during experimentation without touching DeepEvalAdapter's logic.
"""
from __future__ import annotations

FAITHFULNESS_THRESHOLD = 0.5
HALLUCINATION_THRESHOLD = 0.5
ANSWER_RELEVANCY_THRESHOLD = 0.5

# Groq exposes an OpenAI-compatible endpoint, so DeepEval's own LocalModel
# (normally used for vLLM/LM Studio/Ollama) can talk to it directly with no
# custom DeepEvalBaseLLM subclass. Swapping to another OpenAI-compatible
# provider later is a change to these constants, not to any code.
JUDGE_MODEL_NAME = "llama-3.3-70b-versatile"
JUDGE_MODEL_BASE_URL = "https://api.groq.com/openai/v1"
JUDGE_MODEL_TEMPERATURE = 0
