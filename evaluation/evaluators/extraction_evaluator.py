from __future__ import annotations

import math
from typing import TYPE_CHECKING

from models.evaluation_result import EvaluationResult, FieldResult, StackFieldResult

if TYPE_CHECKING:
    from src.Domain.Entity.analyzed_post import AnalyzedPost
    from models.gold_sample import GoldSample


class ExtractionEvaluator:
    """Compares an AnalyzedPost (pipeline prediction) against a GoldSample (ground truth).

    Produces an EvaluationResult with per-field correctness details.
    No metrics are computed here — that is the responsibility of Phase 8.3.
    """

    def evaluate(
        self,
        sample: GoldSample,
        analyzed_post: AnalyzedPost | None,
    ) -> EvaluationResult:
        if analyzed_post is None:
            return self._all_incorrect(sample)

        return EvaluationResult(
            sample_id=sample.raw_post_id,
            company=self._cmp_optional_str(sample.expected_company, analyzed_post.company),
            title=self._cmp_optional_str(sample.expected_title, analyzed_post.title),
            contract=self._cmp_str(sample.expected_contract, analyzed_post.detected_contract_type.value),
            location=self._cmp_optional_str(sample.expected_location, analyzed_post.location),
            remote=self._cmp_str(sample.expected_remote, analyzed_post.detected_remote_mode.value),
            stack=self._cmp_stack(sample.expected_stack, list(analyzed_post.detected_stack)),
            tjm=self._cmp_optional_float(sample.expected_tjm, analyzed_post.detected_tjm),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _all_incorrect(self, sample: GoldSample) -> EvaluationResult:
        """Return an EvaluationResult where every field is marked incorrect."""
        false_field = FieldResult(expected=None, actual=None, correct=False)
        false_stack = StackFieldResult(
            expected=sample.expected_stack,
            actual=[],
            correct=False,
            missing=list(sample.expected_stack),
            unexpected=[],
        )
        return EvaluationResult(
            sample_id=sample.raw_post_id,
            company=false_field,
            title=false_field,
            contract=FieldResult(expected=sample.expected_contract, actual=None, correct=False),
            location=false_field,
            remote=FieldResult(expected=sample.expected_remote, actual=None, correct=False),
            stack=false_stack,
            tjm=FieldResult(expected=sample.expected_tjm, actual=None, correct=False),
        )

    def _cmp_optional_str(self, expected: str | None, actual: str | None) -> FieldResult:
        if expected is None and actual is None:
            return FieldResult(expected=None, actual=None, correct=True)
        if expected is None or actual is None:
            return FieldResult(expected=expected, actual=actual, correct=False)
        correct = expected.strip().lower() == actual.strip().lower()
        return FieldResult(expected=expected, actual=actual, correct=correct)

    def _cmp_str(self, expected: str, actual: str) -> FieldResult:
        correct = expected == actual
        return FieldResult(expected=expected, actual=actual, correct=correct)

    def _cmp_optional_float(self, expected: float | None, actual: float | None) -> FieldResult:
        if expected is None and actual is None:
            return FieldResult(expected=None, actual=None, correct=True)
        if expected is None or actual is None:
            return FieldResult(expected=expected, actual=actual, correct=False)
        correct = math.isclose(expected, actual, rel_tol=0.01)
        return FieldResult(expected=expected, actual=actual, correct=correct)

    def _cmp_stack(self, expected: list[str], actual: list[str]) -> StackFieldResult:
        expected_set = set(expected)
        actual_set = set(actual)
        missing = sorted(expected_set - actual_set)
        unexpected = sorted(actual_set - expected_set)
        correct = not missing and not unexpected
        return StackFieldResult(
            expected=sorted(expected_set),
            actual=sorted(actual_set),
            correct=correct,
            missing=missing,
            unexpected=unexpected,
        )
