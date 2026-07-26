"""LLM-as-a-judge orchestration — the other of the two files in evaluation/
allowed to import the `deepeval` package directly (see judge_model.py)."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, HallucinationMetric
from deepeval.test_case import LLMTestCase

from integrations.deepeval import config
from integrations.deepeval.deepeval_report import DeepEvalReport, MetricOutcome
from integrations.deepeval.judge_input_builder import build_judge_input
from integrations.deepeval.judge_model import build_default_judge_model

if TYPE_CHECKING:
    from src.Domain.Entity.analyzed_post import AnalyzedPost
    from src.Domain.Entity.raw_post import RawPost


class SupportsMeasure(Protocol):
    """Structural type satisfied by both real DeepEval metrics and test Fakes."""

    score: float
    reason: str | None
    success: bool

    def measure(self, test_case: LLMTestCase) -> None: ...


class DeepEvalAdapter:
    """LLM-as-a-judge evaluation of one pipeline extraction, via DeepEval.

    Takes a RawPost + a non-optional AnalyzedPost directly — decoupled from
    EvaluationEngine/GoldSample, since DeepEval judges output quality against
    the source post only and needs no ground-truth expected values. Callers
    are responsible for skipping this adapter entirely when the pipeline
    returned AnalyzedPost=None (not a job offer) — there is nothing
    meaningful to judge in that case; this class does not handle it.

    Complements, never replaces, ExtractionMetricsCalculator/EvaluationReport
    (Phase 8.3's internal rule-based metrics) — produces a DeepEvalReport, a
    structurally different, never-merged report type.

    Metric instances are injectable so unit tests can supply Fake doubles
    instead of exercising DeepEval's real internal LLM-chain logic (which
    requires network access and is impractical to fake faithfully). Only the
    default-construction path (metrics not passed in) builds real DeepEval
    metrics wired to a real judge model.
    """

    def __init__(
        self,
        groq_api_key: str | None = None,
        faithfulness_metric: SupportsMeasure | None = None,
        hallucination_metric: SupportsMeasure | None = None,
        answer_relevancy_metric: SupportsMeasure | None = None,
    ) -> None:
        needs_default_judge = (
            faithfulness_metric is None or hallucination_metric is None or answer_relevancy_metric is None
        )
        judge_model = build_default_judge_model(api_key=groq_api_key or "") if needs_default_judge else None

        self._faithfulness = faithfulness_metric or FaithfulnessMetric(
            threshold=config.FAITHFULNESS_THRESHOLD, model=judge_model, include_reason=True
        )
        self._hallucination = hallucination_metric or HallucinationMetric(
            threshold=config.HALLUCINATION_THRESHOLD, model=judge_model, include_reason=True
        )
        self._answer_relevancy = answer_relevancy_metric or AnswerRelevancyMetric(
            threshold=config.ANSWER_RELEVANCY_THRESHOLD, model=judge_model, include_reason=True
        )

    async def evaluate(self, raw_post: RawPost, analyzed_post: AnalyzedPost) -> DeepEvalReport:
        context = [raw_post.content]
        test_case = LLMTestCase(
            input=raw_post.content,
            actual_output=build_judge_input(analyzed_post),
            context=context,
            retrieval_context=context,
        )

        faithfulness = await self._run_metric(self._faithfulness, test_case)
        hallucination = await self._run_metric(self._hallucination, test_case)
        answer_relevancy = await self._run_metric(self._answer_relevancy, test_case)

        return DeepEvalReport(
            sample_id=raw_post.external_id,
            faithfulness=faithfulness,
            hallucination=hallucination,
            answer_relevancy=answer_relevancy,
        )

    async def _run_metric(self, metric: SupportsMeasure, test_case: LLMTestCase) -> MetricOutcome:
        a_measure = getattr(metric, "a_measure", None)
        if a_measure is not None:
            await a_measure(test_case)
        else:
            await asyncio.to_thread(metric.measure, test_case)
        return MetricOutcome(score=metric.score, success=metric.success, reason=metric.reason)
