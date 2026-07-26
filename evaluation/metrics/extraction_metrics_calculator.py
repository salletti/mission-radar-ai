from __future__ import annotations

from typing import TYPE_CHECKING

from models.evaluation_report import EvaluationReport
from models.extraction_metrics import ExtractionMetrics

if TYPE_CHECKING:
    from models.evaluation_result import EvaluationResult

_SCALAR_FIELDS = ("company", "title", "contract", "location", "remote", "tjm")


class ExtractionMetricsCalculator:
    """Aggregates a list of EvaluationResult into an EvaluationReport.

    Pure aggregation: no re-evaluation, no I/O, no knowledge of DeepEval/Langfuse.
    """

    def calculate(self, results: list[EvaluationResult]) -> EvaluationReport:
        dataset_size = len(results)
        if dataset_size == 0:
            return EvaluationReport(dataset_size=0, extraction_metrics=self._empty_metrics())

        precision, recall, f1 = self._stack_precision_recall_f1(results)
        metrics = ExtractionMetrics(
            company_accuracy=self._scalar_accuracy(results, "company"),
            title_accuracy=self._scalar_accuracy(results, "title"),
            contract_accuracy=self._scalar_accuracy(results, "contract"),
            location_accuracy=self._scalar_accuracy(results, "location"),
            remote_accuracy=self._scalar_accuracy(results, "remote"),
            tjm_accuracy=self._scalar_accuracy(results, "tjm"),
            stack_precision=precision,
            stack_recall=recall,
            stack_f1=f1,
            overall_accuracy=self._overall_accuracy(results),
        )
        return EvaluationReport(dataset_size=dataset_size, extraction_metrics=metrics)

    def _scalar_accuracy(self, results: list[EvaluationResult], field_name: str) -> float:
        correct = sum(1 for r in results if getattr(r, field_name).correct)
        return correct / len(results)

    def _stack_counts(self, results: list[EvaluationResult]) -> tuple[int, int, int]:
        """Sums (true_positives, false_positives, false_negatives) across the dataset."""
        tp = fp = fn = 0
        for r in results:
            stack = r.stack
            tp += len(stack.expected) - len(stack.missing)
            fp += len(stack.unexpected)
            fn += len(stack.missing)
        return tp, fp, fn

    def _stack_precision_recall_f1(self, results: list[EvaluationResult]) -> tuple[float, float, float]:
        tp, fp, fn = self._stack_counts(results)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return precision, recall, f1

    def _overall_accuracy(self, results: list[EvaluationResult]) -> float:
        total_fields = 0
        correct_fields = 0
        for r in results:
            for field_name in (*_SCALAR_FIELDS, "stack"):
                total_fields += 1
                if getattr(r, field_name).correct:
                    correct_fields += 1
        return correct_fields / total_fields

    def _empty_metrics(self) -> ExtractionMetrics:
        return ExtractionMetrics(
            company_accuracy=0.0,
            title_accuracy=0.0,
            contract_accuracy=0.0,
            location_accuracy=0.0,
            remote_accuracy=0.0,
            tjm_accuracy=0.0,
            stack_precision=0.0,
            stack_recall=0.0,
            stack_f1=0.0,
            overall_accuracy=0.0,
        )
