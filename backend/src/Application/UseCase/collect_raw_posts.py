from src.Application.DTO.collect_posts_command import CollectPostsCommand
from src.Application.Gateway.scraper_gateway import ScraperGateway
from src.Domain.Entity.raw_post import RawPost


class CollectRawPosts:
    """Collecte des posts bruts via le ScraperGateway.
    """

    def __init__(self, scraper: ScraperGateway) -> None:
        self._scraper = scraper

    async def execute(self, command: CollectPostsCommand) -> list[RawPost]:
        return await self._scraper.collect_posts(
            query=command.query,
            limit=command.limit,
        )
