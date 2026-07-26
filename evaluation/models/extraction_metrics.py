from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionMetrics:
    """Aggregate accuracy/precision/recall/F1 for one evaluation run.

    All values are floats in [0, 1], kept at full precision — rounding is
    a presentation-layer concern (README, dashboard, exports), never done here.

    No `stack_accuracy`: stack detection is multi-label classification (any
    subset of ~200 technologies can apply), unlike the other fields which are
    simple single-value classifications where accuracy is meaningful. Precision/
    recall/F1 are the metrics that actually measure multi-label detection quality.
    """

    company_accuracy: float
    title_accuracy: float
    contract_accuracy: float
    location_accuracy: float
    remote_accuracy: float
    tjm_accuracy: float
    stack_precision: float
    stack_recall: float
    stack_f1: float
    overall_accuracy: float
