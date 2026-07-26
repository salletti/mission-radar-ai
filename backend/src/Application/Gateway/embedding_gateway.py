from abc import ABC, abstractmethod


class EmbeddingGateway(ABC):
    """Computes and compares text embeddings. Implemented in Infrastructure/."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]: ...

    @abstractmethod
    async def compute_similarity(
        self, embedding_a: list[float], embedding_b: list[float]
    ) -> float: ...
