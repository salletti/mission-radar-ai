"""Unit tests for SentenceTransformerEmbeddingGateway.compute_similarity().

Tests mathematical behavior with raw float vectors — no model loading.
Uses a minimal subclass that skips __init__ since compute_similarity() never
accesses self._model.
"""
import math
import pytest

from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import (
    SentenceTransformerEmbeddingGateway,
)


class _Gateway(SentenceTransformerEmbeddingGateway):
    def __init__(self) -> None:
        pass  # compute_similarity() does not use self._model


_GW = _Gateway()


async def test_identical_vectors_return_one() -> None:
    score = await _GW.compute_similarity([1.0, 0.0], [1.0, 0.0])

    assert math.isclose(score, 1.0, rel_tol=1e-6)


async def test_orthogonal_vectors_return_zero() -> None:
    score = await _GW.compute_similarity([1.0, 0.0], [0.0, 1.0])

    assert math.isclose(score, 0.0, abs_tol=1e-6)


async def test_close_vectors_return_between_half_and_one() -> None:
    # [0.9, 0.1] normalized: magnitude ≈ sqrt(0.81+0.01) ≈ 0.906
    # cosine([1,0], [0.9,0.1]/|[0.9,0.1]|) is positive and < 1.0
    # Using pre-normalised approximation: [0.995, 0.100] (≈ unit)
    import math as _math
    raw = [0.9, 0.1]
    mag = _math.sqrt(sum(v ** 2 for v in raw))
    normalised = [v / mag for v in raw]

    score = await _GW.compute_similarity([1.0, 0.0], normalised)

    assert 0.5 < score < 1.0


async def test_anti_parallel_vectors_clipped_to_zero() -> None:
    score = await _GW.compute_similarity([1.0, 0.0], [-1.0, 0.0])

    assert score == 0.0


async def test_score_always_in_zero_one_range() -> None:
    score = await _GW.compute_similarity([1.0, 0.0], [0.5, 0.5])

    assert 0.0 <= score <= 1.0


async def test_empty_embedding_a_raises_value_error() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        await _GW.compute_similarity([], [1.0, 0.0])


async def test_empty_embedding_b_raises_value_error() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        await _GW.compute_similarity([1.0, 0.0], [])


async def test_none_embedding_raises_value_error() -> None:
    with pytest.raises(ValueError, match="cannot be None"):
        await _GW.compute_similarity(None, [1.0, 0.0])  # type: ignore[arg-type]


async def test_dimension_mismatch_raises_value_error() -> None:
    with pytest.raises(ValueError, match="dimensions mismatch"):
        await _GW.compute_similarity([1.0, 0.0], [1.0, 0.0, 0.0])
