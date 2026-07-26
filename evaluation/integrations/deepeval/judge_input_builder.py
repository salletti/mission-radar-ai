"""Builds the text representation of a pipeline extraction that the
LLM-as-a-judge evaluates — not a generic AnalyzedPost serialization."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Domain.Entity.analyzed_post import AnalyzedPost


def build_judge_input(analyzed_post: AnalyzedPost) -> str:
    """Render an AnalyzedPost extraction as the text DeepEval will judge.

    DeepEval's Faithfulness/Hallucination/Answer Relevancy metrics only
    accept a plain-string `actual_output` — there is no structured-output
    variant for these 3 metrics. This function decides which extracted
    fields count as claims to be judged and how they are phrased; it does
    not call any LLM and does not know about DeepEval's LLMTestCase.

    Every field is included so Faithfulness/Hallucination can catch invented
    values anywhere in the extraction, not just in `summary` (matches the
    pipeline-wide hallucination rate <= 0.10 threshold in CLAUDE.md, not a
    free-text-summary-only threshold).
    """
    tjm = analyzed_post.detected_tjm if analyzed_post.detected_tjm is not None else "unknown"
    stack = ", ".join(analyzed_post.detected_stack) or "none"
    lines = [
        f"Title: {analyzed_post.title or 'unknown'}",
        f"Company: {analyzed_post.company or 'unknown'}",
        f"Location: {analyzed_post.location or 'unknown'}",
        f"Contract type: {analyzed_post.detected_contract_type.value}",
        f"Remote mode: {analyzed_post.detected_remote_mode.value}",
        f"Seniority: {analyzed_post.seniority or 'unknown'}",
        f"Daily rate (TJM): {tjm}",
        f"Technology stack: {stack}",
        f"Summary: {analyzed_post.summary}",
    ]
    return "\n".join(lines)
