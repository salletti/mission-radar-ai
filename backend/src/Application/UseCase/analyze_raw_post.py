from __future__ import annotations

from typing import TYPE_CHECKING

from src.Application.DTO.analyze_raw_post_result import AnalyzeRawPostResult
from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Service.mission_embedding_builder import MissionEmbeddingBuilder
from src.Domain.Service.mission_normalizer import MissionNormalizer

if TYPE_CHECKING:
    from src.Domain.Entity.raw_post import RawPost


class AnalyzeRawPost:
    """Orchestrates the full analysis pipeline for a single RawPost.

    Chains LLM analysis → is_job_offer gate → MissionNormalizer →
    MissionEmbeddingBuilder → EmbeddingGateway → repository.save().
    Idempotent: re-running on an already-analyzed post returns "already_analyzed".
    """

    def __init__(
        self,
        llm: LLMGateway,
        mission_normalizer: MissionNormalizer,
        mission_embedding_builder: MissionEmbeddingBuilder,
        embedding_gateway: EmbeddingGateway,
        analyzed_post_repository: AnalyzedPostRepository,
    ) -> None:
        self._llm = llm
        self._mission_normalizer = mission_normalizer
        self._mission_embedding_builder = mission_embedding_builder
        self._embedding_gateway = embedding_gateway
        self._analyzed_post_repository = analyzed_post_repository

    async def execute(self, raw_post: RawPost) -> AnalyzeRawPostResult:
        existing = await self._analyzed_post_repository.get_by_raw_post_id(raw_post.id)
        if existing:
            return AnalyzeRawPostResult(status="already_analyzed", analyzed_post_id=existing.id)

        post_analysis = await self._llm.analyze_post(raw_post)

        if not post_analysis.is_job_offer:
            return AnalyzeRawPostResult(status="skipped", reason="not_job_offer")

        analyzed_post = self._mission_normalizer.normalize(raw_post.id, post_analysis)

        matching_text = self._mission_embedding_builder.build_matching_text(analyzed_post)
        analyzed_post.embedding = await self._embedding_gateway.embed_text(matching_text)

        await self._analyzed_post_repository.save(analyzed_post)

        return AnalyzeRawPostResult(
            status="analyzed",
            analyzed_post_id=analyzed_post.id,
            analyzed_post=analyzed_post,
        )
