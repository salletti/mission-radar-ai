from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldResult:
    """Comparison result for a single scalar field."""

    expected: str | float | None
    actual: str | float | None
    correct: bool


@dataclass(frozen=True)
class StackFieldResult:
    """Comparison result for the technology stack (list field)."""

    expected: list[str]
    actual: list[str]
    correct: bool
    missing: list[str]    # in expected but not in actual
    unexpected: list[str] # in actual but not in expected


@dataclass(frozen=True)
class EvaluationResult:
    """Per-field comparison of a pipeline prediction vs. a GoldSample.

    All future metrics (Precision, Recall, F1, Accuracy) are computed
    solely from these fields — no further pipeline access required.
    """

    sample_id: str  # GoldSample.raw_post_id
    company: FieldResult
    title: FieldResult
    contract: FieldResult
    location: FieldResult
    remote: FieldResult
    stack: StackFieldResult
    tjm: FieldResult
