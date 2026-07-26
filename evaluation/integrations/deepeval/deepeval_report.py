from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricOutcome:
    """Result of one DeepEval metric run: score, pass/fail, and judge's reasoning."""

    score: float
    success: bool
    reason: str | None


@dataclass(frozen=True)
class DeepEvalReport:
    """Per-sample LLM-as-a-judge verdict on one pipeline extraction.

    Bundles the 3 DeepEval metric outcomes for a single (RawPost, AnalyzedPost)
    pair. Deliberately per-sample, not a dataset-wide aggregate — mirrors
    EvaluationResult's granularity (Phase 8.2), not EvaluationReport's
    dataset-level aggregation (Phase 8.3). No aggregator, no CI thresholds:
    out of scope for this phase.

    Vocabulary here (faithfulness/hallucination/answer_relevancy) is
    DeepEval-specific by design: if DeepEval is ever replaced, this file is
    expected to change along with the rest of integrations/deepeval/, unlike
    evaluation/models/ which stays framework-agnostic.

    This complements EvaluationReport (Phase 8.3), never replaces it — the
    two report types are never merged.
    """

    sample_id: str  # raw_post.external_id — matches GoldSample.raw_post_id / EvaluationResult.sample_id
    faithfulness: MetricOutcome
    hallucination: MetricOutcome
    answer_relevancy: MetricOutcome
