from __future__ import annotations

from dataclasses import dataclass

from models.extraction_metrics import ExtractionMetrics


@dataclass(frozen=True)
class EvaluationReport:
    """Result of one evaluation campaign: how many samples were evaluated,
    and the aggregate metrics computed from them."""

    dataset_size: int
    extraction_metrics: ExtractionMetrics
