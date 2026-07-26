from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Application.UseCase.analyze_raw_post import AnalyzeRawPost
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Service.mission_embedding_builder import MissionEmbeddingBuilder
from src.Domain.Service.mission_normalizer import MissionNormalizer

from evaluators.extraction_evaluator import ExtractionEvaluator
from models.evaluation_result import EvaluationResult

if TYPE_CHECKING:
    from src.Domain.Entity.raw_post import RawPost
    from models.gold_sample import GoldSample


class EvaluationEngine:
    """Single entry point for the AI evaluation platform.

    Treats the backend as a black box: delegates to the real AnalyzeRawPost
    use case so that any pipeline evolution is automatically inherited.
    Designed to grow across Phase 8.3 (evaluate_dataset) and 8.4 (Langfuse).
    """

    def __init__(
        self,
        llm_gateway: LLMGateway,
        embedding_gateway: EmbeddingGateway,
    ) -> None:
        self._llm = llm_gateway
        self._embedding = embedding_gateway

    async def evaluate_sample(
        self,
        sample: GoldSample,
        raw_post: RawPost,
    ) -> EvaluationResult:
        use_case = AnalyzeRawPost(
            llm=self._llm,
            mission_normalizer=MissionNormalizer(),
            mission_embedding_builder=MissionEmbeddingBuilder(),
            embedding_gateway=self._embedding,
            analyzed_post_repository=_InMemoryAnalyzedPostRepository(),
        )
        result = await use_case.execute(raw_post)
        analyzed_post: AnalyzedPost | None = result.analyzed_post
        return ExtractionEvaluator().evaluate(sample, analyzed_post)


class _InMemoryAnalyzedPostRepository(AnalyzedPostRepository):
    """In-memory AnalyzedPostRepository for evaluation context.

    Bypasses DB persistence so the evaluation engine can call AnalyzeRawPost
    without any side effects. The analyzed_post is retrieved directly from
    AnalyzeRawPostResult rather than from this store.
    """

    async def save(self, analyzed_post: AnalyzedPost) -> None:
        pass

    async def get_by_raw_post_id(self, raw_post_id: UUID) -> AnalyzedPost | None:
        return None

    async def get_by_id(self, post_id: UUID) -> AnalyzedPost | None:
        return None

    async def list_today_missions(self) -> list[AnalyzedPost]:
        return []

    async def list_missions(self, limit: int) -> list[AnalyzedPost]:
        return []

    async def find_by_raw_post_ids(self, raw_post_ids: list[UUID]) -> list[AnalyzedPost]:
        return []

    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]:
        return []
