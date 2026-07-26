import argparse
import asyncio
import sys
from uuid import UUID

from src.Application.DTO.collect_posts_command import CollectPostsCommand
from src.Application.UseCase.collect_raw_posts import CollectRawPosts
from src.Application.UseCase.save_raw_posts import SaveRawPosts, SaveRawPostsResult
from src.Infrastructure.Config.database import AsyncSessionLocal
from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Apify.apify_scraper_gateway import ApifyScraperGateway
from src.Infrastructure.External.Apify.mock_apify_provider import MockApifyProvider
from src.Infrastructure.External.Apify.real_apify_provider import RealApifyProvider
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from src.Infrastructure.Persistence.Repository.search_query_raw_post_repository import SqlAlchemySearchQueryRawPostRepository

_CONTENT_PREVIEW_LENGTH = 120


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect LinkedIn posts via scraping")
    parser.add_argument("--query", default="symfony freelance paris", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Max number of posts to collect")
    parser.add_argument(
        "--provider",
        choices=["mock", "real"],
        default="mock",
        help="Provider to use : mock (fixtures JSON) or real (Apify API)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Persist collected posts to PostgreSQL (skips duplicates)",
    )
    parser.add_argument(
        "--search-query-id",
        dest="search_query_id",
        default=None,
        help="UUID of the SearchQuery to link posts to (required with --save)",
    )
    return parser.parse_args(argv)


def _print_posts(posts: list, query: str) -> None:
    print("=" * 50)
    print("MISSION RADAR AI")
    print("Collect Posts")
    print("=" * 50)
    print(f"\nQuery : {query}")
    print(f"Posts found : {len(posts)}\n")
    for i, post in enumerate(posts, start=1):
        print("-" * 50)
        print(f"\n[{i}]\n")
        print(f"Author :\n{post.author_name}\n")
        print(f"Published :\n{post.published_at.date()}\n")
        print(f"Source :\n{post.source}\n")
        print(f"URL :\n{post.post_url}\n")
        preview = post.content[:_CONTENT_PREVIEW_LENGTH].replace("\n", " ")
        if len(post.content) > _CONTENT_PREVIEW_LENGTH:
            preview += "…"
        print(f"Content preview :\n{preview}\n")
    print("-" * 50)


def _print_save_result(result: SaveRawPostsResult) -> None:
    print("\n" + "=" * 50)
    print(f"Posts collected    : {result.total}")
    print(f"New posts saved    : {result.saved}")
    print(f"Duplicates skipped : {result.skipped}")
    print(f"Links created      : {result.links_created}")
    print("=" * 50)


async def _run(
    query: str,
    limit: int,
    provider: str = "mock",
    save: bool = False,
    search_query_id: str | None = None,
) -> None:
    if save and not search_query_id:
        print("Error: --search-query-id is required with --save", file=sys.stderr)
        sys.exit(1)

    if provider == "real":
        posts_provider = RealApifyProvider(settings.APIFY_API_TOKEN)
    else:
        posts_provider = MockApifyProvider()
    gateway = ApifyScraperGateway(posts_provider)
    posts = await CollectRawPosts(gateway).execute(CollectPostsCommand(query=query, limit=limit))
    _print_posts(posts, query)

    if save:
        async with AsyncSessionLocal() as session:
            raw_repo = SqlAlchemyRawPostRepository(session)
            link_repo = SqlAlchemySearchQueryRawPostRepository(session)
            result = await SaveRawPosts(raw_repo, link_repo).execute(posts, UUID(search_query_id))  # type: ignore[arg-type]
            await session.commit()
        _print_save_result(result)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        asyncio.run(_run(args.query, args.limit, args.provider, args.save, args.search_query_id))
    except Exception as e:
        print(f"Error while collecting posts:\n{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
