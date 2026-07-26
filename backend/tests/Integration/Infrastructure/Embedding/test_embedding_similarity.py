"""Integration tests for SentenceTransformerEmbeddingGateway.compute_similarity().

Uses the real model — validates that semantic similarity actually works
as expected on job-domain phrases. No database required.
"""

from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import (
    SentenceTransformerEmbeddingGateway,
)

_GATEWAY = SentenceTransformerEmbeddingGateway()


async def test_synonymous_job_titles_score_above_half() -> None:
    a = await _GATEWAY.embed_text("python developer")
    b = await _GATEWAY.embed_text("python engineer")

    score = await _GATEWAY.compute_similarity(a, b)

    assert score > 0.5, f"Expected synonymous titles to score > 0.5, got {score:.4f}"


async def test_unrelated_professions_score_below_half() -> None:
    a = await _GATEWAY.embed_text("python developer")
    b = await _GATEWAY.embed_text("accountant payroll")

    score = await _GATEWAY.compute_similarity(a, b)

    assert score < 0.5, f"Expected unrelated professions to score < 0.5, got {score:.4f}"


async def test_similar_scores_higher_than_unrelated() -> None:
    dev = await _GATEWAY.embed_text("python developer")
    engineer = await _GATEWAY.embed_text("python engineer")
    accountant = await _GATEWAY.embed_text("accountant payroll")

    score_similar = await _GATEWAY.compute_similarity(dev, engineer)
    score_unrelated = await _GATEWAY.compute_similarity(dev, accountant)

    assert score_similar > score_unrelated, (
        f"Expected similar pair ({score_similar:.4f}) > unrelated pair ({score_unrelated:.4f})"
    )
