"""Tests for DeepEvalAdapter — fake DeepEval metrics, no real deepeval LLM
calls, no network. Real metric construction (default path) is exercised
structurally only — never via .evaluate(), which would require network."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, HallucinationMetric
from deepeval.test_case import LLMTestCase

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.raw_post import RawPost
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode

from integrations.deepeval.deepeval_adapter import DeepEvalAdapter
from integrations.deepeval.judge_input_builder import build_judge_input

_NOW = datetime(2026, 7, 5, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeMetric:
    """Records the LLMTestCase it received; returns a canned score/reason/success."""

    def __init__(self, score: float, success: bool, reason: str | None) -> None:
        self.score = score
        self.success = success
        self.reason = reason
        self.received_test_case: LLMTestCase | None = None
        self.measure_called = False
        self.a_measure_called = False

    def measure(self, test_case: LLMTestCase) -> None:
        self.measure_called = True
        self.received_test_case = test_case

    async def a_measure(self, test_case: LLMTestCase) -> None:
        self.a_measure_called = True
        self.received_test_case = test_case


class _FakeMetricNoAsyncSupport:
    """Same as _FakeMetric but has NO a_measure — forces the asyncio.to_thread fallback."""

    def __init__(self, score: float, success: bool, reason: str | None) -> None:
        self.score = score
        self.success = success
        self.reason = reason
        self.received_test_case: LLMTestCase | None = None
        self.measure_called = False

    def measure(self, test_case: LLMTestCase) -> None:
        self.measure_called = True
        self.received_test_case = test_case


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw_post(**kwargs) -> RawPost:
    defaults = dict(
        source="linkedin",
        external_id="urn:li:activity:1111111111111111111",
        author_name="Recruiter",
        author_url="",
        content="Mission Python Senior freelance Paris hybride 650€/j",
        post_url="",
        published_at=_NOW,
        scraped_at=_NOW,
    )
    defaults.update(kwargs)
    return RawPost(**defaults)


def _make_analyzed_post(**kwargs) -> AnalyzedPost:
    defaults = dict(
        raw_post_id=uuid4(),
        summary="Mission freelance Python Senior à Paris",
        detected_stack=("python", "fastapi"),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.HYBRID,
        title="Développeur Python Senior",
        company="Accenture",
        location="Paris, France",
        detected_tjm=650.0,
    )
    defaults.update(kwargs)
    return AnalyzedPost(**defaults)


def _make_adapter(faithfulness=None, hallucination=None, answer_relevancy=None) -> DeepEvalAdapter:
    return DeepEvalAdapter(
        faithfulness_metric=faithfulness or _FakeMetric(score=0.9, success=True, reason="looks faithful"),
        hallucination_metric=hallucination or _FakeMetric(score=0.1, success=True, reason="no hallucination"),
        answer_relevancy_metric=answer_relevancy or _FakeMetric(score=0.8, success=True, reason="relevant"),
    )


# ---------------------------------------------------------------------------
# evaluate()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_returns_deepeval_report_with_sample_id_from_external_id() -> None:
    adapter = _make_adapter()
    report = await adapter.evaluate(_make_raw_post(), _make_analyzed_post())
    assert report.sample_id == "urn:li:activity:1111111111111111111"


@pytest.mark.asyncio
async def test_evaluate_populates_all_three_metric_outcomes() -> None:
    faithfulness = _FakeMetric(score=0.95, success=True, reason="faithful reason")
    hallucination = _FakeMetric(score=0.05, success=True, reason="no hallucination reason")
    answer_relevancy = _FakeMetric(score=0.7, success=True, reason="relevancy reason")
    adapter = _make_adapter(faithfulness, hallucination, answer_relevancy)

    report = await adapter.evaluate(_make_raw_post(), _make_analyzed_post())

    assert report.faithfulness.score == 0.95
    assert report.faithfulness.reason == "faithful reason"
    assert report.hallucination.score == 0.05
    assert report.hallucination.reason == "no hallucination reason"
    assert report.answer_relevancy.score == 0.7
    assert report.answer_relevancy.reason == "relevancy reason"


@pytest.mark.asyncio
async def test_evaluate_builds_test_case_with_raw_post_content_as_input() -> None:
    faithfulness = _FakeMetric(score=0.9, success=True, reason=None)
    adapter = _make_adapter(faithfulness=faithfulness)
    raw_post = _make_raw_post(content="A very specific post body")

    await adapter.evaluate(raw_post, _make_analyzed_post())

    assert faithfulness.received_test_case.input == "A very specific post body"


@pytest.mark.asyncio
async def test_evaluate_builds_test_case_actual_output_from_judge_input_builder() -> None:
    faithfulness = _FakeMetric(score=0.9, success=True, reason=None)
    adapter = _make_adapter(faithfulness=faithfulness)
    analyzed_post = _make_analyzed_post()

    await adapter.evaluate(_make_raw_post(), analyzed_post)

    assert faithfulness.received_test_case.actual_output == build_judge_input(analyzed_post)


@pytest.mark.asyncio
async def test_evaluate_sets_both_context_and_retrieval_context_to_raw_post_content() -> None:
    faithfulness = _FakeMetric(score=0.9, success=True, reason=None)
    hallucination = _FakeMetric(score=0.1, success=True, reason=None)
    answer_relevancy = _FakeMetric(score=0.8, success=True, reason=None)
    adapter = _make_adapter(faithfulness, hallucination, answer_relevancy)
    raw_post = _make_raw_post(content="Source of truth text")

    await adapter.evaluate(raw_post, _make_analyzed_post())

    for metric in (faithfulness, hallucination, answer_relevancy):
        assert metric.received_test_case.context == ["Source of truth text"]
        assert metric.received_test_case.retrieval_context == ["Source of truth text"]


@pytest.mark.asyncio
async def test_evaluate_calls_a_measure_when_available() -> None:
    faithfulness = _FakeMetric(score=0.9, success=True, reason=None)
    adapter = _make_adapter(faithfulness=faithfulness)

    await adapter.evaluate(_make_raw_post(), _make_analyzed_post())

    assert faithfulness.a_measure_called is True
    assert faithfulness.measure_called is False


@pytest.mark.asyncio
async def test_evaluate_falls_back_to_sync_measure_when_a_measure_missing() -> None:
    faithfulness = _FakeMetricNoAsyncSupport(score=0.42, success=True, reason="sync path")
    adapter = _make_adapter(faithfulness=faithfulness)

    report = await adapter.evaluate(_make_raw_post(), _make_analyzed_post())

    assert faithfulness.measure_called is True
    assert report.faithfulness.score == 0.42
    assert report.faithfulness.reason == "sync path"


# ---------------------------------------------------------------------------
# Default construction (structural only — never call .evaluate() on this path,
# it would require network access and a real Groq API key)
# ---------------------------------------------------------------------------


def test_default_construction_builds_real_deepeval_metrics() -> None:
    adapter = DeepEvalAdapter(groq_api_key="fake-key-not-used")
    assert isinstance(adapter._faithfulness, FaithfulnessMetric)
    assert isinstance(adapter._hallucination, HallucinationMetric)
    assert isinstance(adapter._answer_relevancy, AnswerRelevancyMetric)


def test_default_construction_reads_thresholds_from_config() -> None:
    from integrations.deepeval import config

    adapter = DeepEvalAdapter(groq_api_key="fake-key-not-used")
    assert adapter._faithfulness.threshold == config.FAITHFULNESS_THRESHOLD
    assert adapter._hallucination.threshold == config.HALLUCINATION_THRESHOLD
    assert adapter._answer_relevancy.threshold == config.ANSWER_RELEVANCY_THRESHOLD


def test_partial_injection_only_builds_missing_metrics_for_real() -> None:
    faithfulness = _FakeMetric(score=0.9, success=True, reason=None)
    adapter = DeepEvalAdapter(groq_api_key="fake-key-not-used", faithfulness_metric=faithfulness)
    assert adapter._faithfulness is faithfulness
    assert isinstance(adapter._hallucination, HallucinationMetric)
    assert isinstance(adapter._answer_relevancy, AnswerRelevancyMetric)
