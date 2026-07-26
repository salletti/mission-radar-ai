from __future__ import annotations

import asyncio
import numpy as np
from functools import partial

from sentence_transformers import SentenceTransformer

from src.Application.Gateway.embedding_gateway import EmbeddingGateway


class SentenceTransformerEmbeddingGateway(EmbeddingGateway):
    """Embedding gateway backed by sentence-transformers (all-MiniLM-L6-v2 by default).

    SentenceTransformer.encode() is synchronous — wrapped in run_in_executor to
    avoid blocking the async event loop during embedding generation.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model = SentenceTransformer(model_name)

    async def embed_text(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        vector = await loop.run_in_executor(
            None, partial(self._model.encode, text, normalize_embeddings=True)
        )
        return vector.tolist()

    async def compute_similarity(
        self, embedding_a: list[float], embedding_b: list[float]
    ) -> float:
        if embedding_a is None or embedding_b is None:
            raise ValueError("Embedding cannot be None")
        if not embedding_a or not embedding_b:
            raise ValueError("Embedding cannot be empty")
        if len(embedding_a) != len(embedding_b):
            raise ValueError(
                f"Embedding dimensions mismatch: {len(embedding_a)} != {len(embedding_b)}"
            )
        va = np.array(embedding_a)
        vb = np.array(embedding_b)
        norm = np.linalg.norm(va) * np.linalg.norm(vb)
        return max(0.0, float(np.dot(va, vb) / norm)) if norm > 0 else 0.0
