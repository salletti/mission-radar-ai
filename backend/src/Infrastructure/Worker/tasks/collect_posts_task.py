import asyncio
import logging
from uuid import UUID

from src.Application.DTO.collect_posts_command import CollectPostsCommand
from src.Application.UseCase.collect_raw_posts import CollectRawPosts
from src.Application.UseCase.save_raw_posts import SaveRawPosts
from src.Infrastructure.Config.database import CeleryAsyncSessionLocal as AsyncSessionLocal
from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Apify.apify_scraper_gateway import ApifyScraperGateway
from src.Infrastructure.External.Apify.mock_apify_provider import MockApifyProvider
from src.Infrastructure.External.Apify.real_apify_provider import RealApifyProvider
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from src.Infrastructure.Persistence.Repository.search_query_raw_post_repository import SqlAlchemySearchQueryRawPostRepository
from src.Infrastructure.Worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.collect_posts", ignore_result=True)
def collect_posts(query: str, limit: int = 10, search_query_id: str = "") -> None:
    """Celery task : collecte et persiste des posts LinkedIn. Résultat ignoré — vérité dans PostgreSQL."""
    result = asyncio.run(_collect(query, limit, search_query_id))
    logger.info(
        "collect_posts completed | query=%r limit=%d | collected=%d saved=%d skipped=%d dispatched=%d links=%d",
        query,
        limit,
        result["posts_collected"],
        result["posts_saved"],
        result["duplicates_skipped"],
        result["analyses_dispatched"],
        result["links_created"],
    )


async def _collect(query: str, limit: int, search_query_id: str) -> dict:
    if settings.APIFY_PROVIDER == "real":
        provider = RealApifyProvider(settings.APIFY_API_TOKEN)
    else:
        provider = MockApifyProvider()
    gateway = ApifyScraperGateway(provider)
    posts = await CollectRawPosts(gateway).execute(CollectPostsCommand(query=query, limit=limit))

    async with AsyncSessionLocal() as session:
        raw_repo = SqlAlchemyRawPostRepository(session)
        link_repo = SqlAlchemySearchQueryRawPostRepository(session)
        result = await SaveRawPosts(raw_repo, link_repo).execute(posts, UUID(search_query_id))
        await session.commit()

    for post_id in result.new_post_ids:
        celery_app.send_task("tasks.analyze_post", args=[str(post_id)])

    return {
        "posts_collected": result.total,
        "posts_saved": result.saved,
        "duplicates_skipped": result.skipped,
        "analyses_dispatched": len(result.new_post_ids),
        "links_created": result.links_created,
    }
