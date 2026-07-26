from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.Infrastructure.External.Apify.posts_provider import PostsProvider
from src.Application.Gateway.scraper_gateway import ScraperGateway
from src.Domain.Entity.raw_post import RawPost

logger = logging.getLogger(__name__)


class ApifyScraperGateway(ScraperGateway):
    """Implémente ScraperGateway en s'appuyant sur PostsProvider.

    Responsabilité unique : mapper les dicts bruts Apify en objets domaine RawPost.
    Aucun appel HTTP direct, aucune persistance.
    """

    def __init__(self, provider: PostsProvider) -> None:
        self._provider = provider

    async def collect_posts(self, query: str, limit: int) -> list[RawPost]:
        raw_data = await self._provider.search_posts(query=query, limit=limit)
        scraped_at = datetime.now(timezone.utc)
        posts: list[RawPost] = []
        for i, item in enumerate(raw_data):
            post = self._map_post(item, scraped_at, index=i)
            if post is not None:
                posts.append(post)
        return posts

    def _map_post(self, data: dict, scraped_at: datetime, *, index: int = 0) -> RawPost | None:
        external_id = data.get("id")
        if not external_id:
            logger.warning("Post[%d] ignoré : champ 'id' absent", index)
            return None

        content = data.get("content") or ""
        if not content.strip():
            logger.warning("Post[%d] (id=%s) ignoré : contenu absent ou vide", index, external_id)
            return None

        author = data.get("author") or {}
        author_name: str = author.get("name") or ""
        author_url: str = author.get("linkedinUrl") or ""

        post_url: str = data.get("linkedinUrl") or ""

        posted_at_block = data.get("postedAt") or {}
        date_str: str | None = posted_at_block.get("date")
        if date_str:
            try:
                published_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                logger.warning("Post[%d] (id=%s) : date invalide '%s', fallback sur now()", index, external_id, date_str)
                published_at = scraped_at
        else:
            published_at = scraped_at

        return RawPost(
            source="linkedin",
            external_id=str(external_id),
            author_name=author_name,
            author_url=author_url,
            content=content,
            post_url=post_url,
            published_at=published_at,
            scraped_at=scraped_at,
        )
