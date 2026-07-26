"""Unit tests for SentenceTransformerEmbeddingGateway.

Uses the real SentenceTransformer model — the gateway IS the I/O boundary.
No mocking of the model; this follows the same pattern as test_pdfminer_cv_extractor_gateway.py.
"""
import pytest

from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import (
    SentenceTransformerEmbeddingGateway,
)

_GATEWAY = SentenceTransformerEmbeddingGateway()


async def test_embed_text_returns_384_floats() -> None:
    result = await _GATEWAY.embed_text("Senior Python Developer, 10 years, FastAPI, Docker")

    assert len(result) == 384
    assert all(isinstance(v, float) for v in result)


async def test_embed_text_deterministic() -> None:
    text = "Freelance Symfony Developer, full remote, Paris"

    first = await _GATEWAY.embed_text(text)
    second = await _GATEWAY.embed_text(text)

    assert first == second


async def test_compute_similarity_identical_texts() -> None:
    text = "Senior Python Developer"
    embedding = await _GATEWAY.embed_text(text)

    similarity = await _GATEWAY.compute_similarity(embedding, embedding)

    assert similarity >= 0.99


async def test_compute_similarity_different_texts() -> None:
    emb_python = await _GATEWAY.embed_text("Python Developer, FastAPI, Docker")
    emb_java = await _GATEWAY.embed_text("Java Developer, Spring Boot, Maven")

    similarity = await _GATEWAY.compute_similarity(emb_python, emb_java)

    assert 0.0 <= similarity < 1.0


async def test_compute_similarity_zero_vector() -> None:
    zero = [0.0] * 384
    normal = await _GATEWAY.embed_text("some text")

    result = await _GATEWAY.compute_similarity(zero, normal)

    assert result == 0.0
