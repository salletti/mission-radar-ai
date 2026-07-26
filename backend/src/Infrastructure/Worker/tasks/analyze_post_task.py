import asyncio
import logging
from functools import lru_cache
from uuid import UUID

from src.Application.UseCase.analyze_raw_post import AnalyzeRawPost
from src.Domain.Service.mission_embedding_builder import MissionEmbeddingBuilder
from src.Domain.Service.mission_normalizer import MissionNormalizer
from src.Infrastructure.Config.database import CeleryAsyncSessionLocal as AsyncSessionLocal
from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import SentenceTransformerEmbeddingGateway
from src.Infrastructure.External.LLM.exceptions import LLMExtractionError
from src.Infrastructure.External.LLM.groq_llm_gateway import GroqLLMGateway
from src.Infrastructure.External.Observability.langfuse.factory import get_langfuse_tracer
from src.Infrastructure.Persistence.Repository.analyzed_post_repository import SqlAlchemyAnalyzedPostRepository
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from src.Infrastructure.Worker.celery_app import celery_app


@lru_cache(maxsize=1)
def _get_embedding_gateway() -> SentenceTransformerEmbeddingGateway:
    """Singleton — loads all-MiniLM-L6-v2 once per worker process."""
    return SentenceTransformerEmbeddingGateway()

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.analyze_post", bind=True, max_retries=3)
def analyze_post_task(self, raw_post_id: str) -> dict:
    """Celery task : analyse un RawPost et persiste l'AnalyzedPost. Aucune logique métier ici."""
    try:
        result = asyncio.run(_analyze(raw_post_id))
        logger.info(
            "analyze_post completed | raw_post_id=%s status=%s",
            raw_post_id,
            result["status"],
        )
        return result
    except LLMExtractionError as e:
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
    except ValueError:
        logger.error("analyze_post: RawPost not found | raw_post_id=%s", raw_post_id)
        raise


async def _analyze(raw_post_id: str) -> dict:
    async with AsyncSessionLocal() as session:
        raw_post_repo = SqlAlchemyRawPostRepository(session)
        raw_post = await raw_post_repo.get_by_id(UUID(raw_post_id))
        if raw_post is None:
            raise ValueError(f"RawPost {raw_post_id} not found")

        llm = GroqLLMGateway(settings.GROQ_API_KEY, tracer=get_langfuse_tracer())
        analyzed_post_repo = SqlAlchemyAnalyzedPostRepository(session)
        use_case = AnalyzeRawPost(
            llm=llm,
            mission_normalizer=MissionNormalizer(),
            mission_embedding_builder=MissionEmbeddingBuilder(),
            embedding_gateway=_get_embedding_gateway(),
            analyzed_post_repository=analyzed_post_repo,
        )
        result = await use_case.execute(raw_post)
        await session.commit()

    return {
        "status": result.status,
        "analyzed_post_id": str(result.analyzed_post_id) if result.analyzed_post_id else None,
    }
