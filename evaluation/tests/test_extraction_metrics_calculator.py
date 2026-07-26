"""Tests for ExtractionMetricsCalculator — pure aggregation, no evaluator/engine involved."""
from __future__ import annotations

import pytest

from metrics.extraction_metrics_calculator import ExtractionMetricsCalculator
from models.evaluation_result import EvaluationResult, FieldResult, StackFieldResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _field(correct: bool) -> FieldResult:
    return FieldResult(expected="x", actual="x" if correct else "y", correct=correct)


def _stack(expected: list[str], missing: list[str], unexpected: list[str]) -> StackFieldResult:
    actual = sorted((set(expected) - set(missing)) | set(unexpected))
    correct = not missing and not unexpected
    return StackFieldResult(
        expected=expected, actual=actual, correct=correct, missing=missing, unexpected=unexpected
    )


def _result(sample_id: str = "s1", **overrides) -> EvaluationResult:
    defaults = dict(
        sample_id=sample_id,
        company=_field(True),
        title=_field(True),
        contract=_field(True),
        location=_field(True),
        remote=_field(True),
        tjm=_field(True),
        stack=_stack(expected=["python"], missing=[], unexpected=[]),
    )
    defaults.update(overrides)
    return EvaluationResult(**defaults)


_CALCULATOR = ExtractionMetricsCalculator()


# ---------------------------------------------------------------------------
# Perfect dataset
# ---------------------------------------------------------------------------


def test_perfect_dataset_all_metrics_are_one() -> None:
    report = _CALCULATOR.calculate([_result("s1"), _result("s2")])
    assert report.dataset_size == 2
    m = report.extraction_metrics
    assert m.company_accuracy == 1.0
    assert m.title_accuracy == 1.0
    assert m.contract_accuracy == 1.0
    assert m.location_accuracy == 1.0
    assert m.remote_accuracy == 1.0
    assert m.tjm_accuracy == 1.0
    assert m.stack_precision == 1.0
    assert m.stack_recall == 1.0
    assert m.stack_f1 == 1.0
    assert m.overall_accuracy == 1.0


# ---------------------------------------------------------------------------
# Fully wrong dataset
# ---------------------------------------------------------------------------


def test_fully_wrong_dataset_all_metrics_are_zero() -> None:
    def _all_wrong(sample_id: str) -> EvaluationResult:
        return _result(
            sample_id,
            company=_field(False),
            title=_field(False),
            contract=_field(False),
            location=_field(False),
            remote=_field(False),
            tjm=_field(False),
            stack=_stack(expected=["python", "docker"], missing=["python", "docker"], unexpected=[]),
        )

    report = _CALCULATOR.calculate([_all_wrong("s1"), _all_wrong("s2")])
    m = report.extraction_metrics
    assert m.company_accuracy == 0.0
    assert m.title_accuracy == 0.0
    assert m.contract_accuracy == 0.0
    assert m.location_accuracy == 0.0
    assert m.remote_accuracy == 0.0
    assert m.tjm_accuracy == 0.0
    assert m.stack_precision == 0.0
    assert m.stack_recall == 0.0
    assert m.stack_f1 == 0.0
    assert m.overall_accuracy == 0.0


# ---------------------------------------------------------------------------
# Mixed dataset — hand-computed expected values
# ---------------------------------------------------------------------------


def test_mixed_dataset_computed_values() -> None:
    s1 = _result(
        "s1",
        stack=_stack(expected=["python", "fastapi", "docker"], missing=["docker"], unexpected=[]),
    )
    s2 = _result(
        "s2",
        title=_field(False),
        remote=_field(False),
        stack=_stack(expected=["python"], missing=[], unexpected=["kubernetes"]),
    )
    s3 = _result(
        "s3",
        company=_field(False),
        contract=_field(False),
        tjm=_field(False),
        stack=_stack(expected=["python", "docker"], missing=[], unexpected=[]),
    )

    report = _CALCULATOR.calculate([s1, s2, s3])
    m = report.extraction_metrics

    assert report.dataset_size == 3
    assert m.company_accuracy == 2 / 3
    assert m.title_accuracy == 2 / 3
    assert m.contract_accuracy == 2 / 3
    assert m.location_accuracy == 1.0
    assert m.remote_accuracy == 2 / 3
    assert m.tjm_accuracy == 2 / 3

    # stack: TP = (3-1) + (1-0) + (2-0) = 5, FP = 0+1+0 = 1, FN = 1+0+0 = 1
    assert m.stack_precision == 5 / 6
    assert m.stack_recall == 5 / 6
    assert m.stack_f1 == 5 / 6  # precision == recall here, useful sanity check

    # overall: correct fields = 6 (s1) + 4 (s2) + 4 (s3) = 14 out of 7*3 = 21
    assert m.overall_accuracy == 14 / 21


# ---------------------------------------------------------------------------
# Fields are computed independently of one another
# ---------------------------------------------------------------------------


def test_company_accuracy_independent_of_other_fields() -> None:
    results = [
        _result("s1"),
        _result("s2"),
        _result("s3", company=_field(False)),
        _result("s4", company=_field(False)),
    ]
    m = _CALCULATOR.calculate(results).extraction_metrics
    assert m.company_accuracy == 0.5
    assert m.title_accuracy == 1.0
    assert m.contract_accuracy == 1.0
    assert m.location_accuracy == 1.0
    assert m.remote_accuracy == 1.0
    assert m.tjm_accuracy == 1.0


# ---------------------------------------------------------------------------
# Stack precision / recall / F1 in isolation
# ---------------------------------------------------------------------------


def test_stack_precision_reflects_false_positives_only() -> None:
    result = _result("s1", stack=_stack(expected=["python"], missing=[], unexpected=["docker"]))
    m = _CALCULATOR.calculate([result]).extraction_metrics
    assert m.stack_precision == 0.5  # tp=1, fp=1
    assert m.stack_recall == 1.0  # fn=0


def test_stack_recall_reflects_false_negatives_only() -> None:
    result = _result("s1", stack=_stack(expected=["python", "docker"], missing=["docker"], unexpected=[]))
    m = _CALCULATOR.calculate([result]).extraction_metrics
    assert m.stack_precision == 1.0  # tp=1, fp=0
    assert m.stack_recall == 0.5  # fn=1


def test_stack_f1_is_harmonic_mean_not_arithmetic_mean() -> None:
    result = _result("s1", stack=_stack(expected=["python", "docker"], missing=["docker"], unexpected=[]))
    m = _CALCULATOR.calculate([result]).extraction_metrics
    assert m.stack_precision == 1.0
    assert m.stack_recall == 0.5
    assert m.stack_f1 == pytest.approx(2 / 3)
    assert m.stack_f1 != 0.75  # the (wrong) arithmetic mean of precision and recall


def test_stack_precision_and_recall_zero_when_no_true_positives() -> None:
    result = _result("s1", stack=_stack(expected=["python"], missing=["python"], unexpected=["docker"]))
    m = _CALCULATOR.calculate([result]).extraction_metrics
    assert m.stack_precision == 0.0
    assert m.stack_recall == 0.0
    assert m.stack_f1 == 0.0


# ---------------------------------------------------------------------------
# Overall accuracy — 7 uniform fields per sample, stack counts as one
# ---------------------------------------------------------------------------


def test_overall_accuracy_denominator_is_seven_times_dataset_size() -> None:
    results = [
        _result("s1", company=_field(False)),
        _result("s2", title=_field(False)),
        _result("s3", stack=_stack(expected=["python"], missing=["python"], unexpected=[])),
    ]
    m = _CALCULATOR.calculate(results).extraction_metrics
    # 3 samples * 7 fields = 21 total; 3 fields wrong (1 per sample) => 18 correct
    assert m.overall_accuracy == 18 / 21


def test_overall_accuracy_treats_stack_as_a_single_field() -> None:
    """A large stack mismatch must not outweigh a single scalar field mismatch."""
    result = _result(
        "s1",
        company=_field(False),
        stack=_stack(expected=["a", "b", "c", "d", "e"], missing=["a", "b", "c", "d", "e"], unexpected=[]),
    )
    m = _CALCULATOR.calculate([result]).extraction_metrics
    # 7 fields total, 2 wrong (company + stack) regardless of stack's item count
    assert m.overall_accuracy == 5 / 7


# ---------------------------------------------------------------------------
# Empty dataset
# ---------------------------------------------------------------------------


def test_empty_results_returns_zeroed_report() -> None:
    report = _CALCULATOR.calculate([])
    assert report.dataset_size == 0
    m = report.extraction_metrics
    assert m.company_accuracy == 0.0
    assert m.title_accuracy == 0.0
    assert m.contract_accuracy == 0.0
    assert m.location_accuracy == 0.0
    assert m.remote_accuracy == 0.0
    assert m.tjm_accuracy == 0.0
    assert m.stack_precision == 0.0
    assert m.stack_recall == 0.0
    assert m.stack_f1 == 0.0
    assert m.overall_accuracy == 0.0


# ---------------------------------------------------------------------------
# dataset_size
# ---------------------------------------------------------------------------


def test_dataset_size_matches_input_length() -> None:
    results = [_result(f"s{i}") for i in range(5)]
    report = _CALCULATOR.calculate(results)
    assert report.dataset_size == 5
