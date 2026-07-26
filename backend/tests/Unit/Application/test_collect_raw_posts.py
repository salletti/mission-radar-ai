"""Unit tests for CollectRawPosts use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone

from src.Application.DTO.collect_posts_command import CollectPostsCommand
from src.Application.Gateway.scraper_gateway import ScraperGateway
from src.Application.UseCase.collect_raw_posts import CollectRawPosts
from src.Domain.Entity.raw_post import RawPost

_NOW = datetime(2026, 6, 14, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fake implementations
# ---------------------------------------------------------------------------


class FakeScraperGateway(ScraperGateway):
    def __init__(self, posts: list[RawPost] | None = None) -> None:
        self.calls: list[tuple[str, int]] = []
        self._posts = posts if posts is not None else [_make_raw_post("fake-001"), _make_raw_post("fake-002")]

    async def collect_posts(self, query: str, limit: int) -> list[RawPost]:
        self.calls.append((query, limit))
        return self._posts[:limit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw_post(external_id: str = "fake-001") -> RawPost:
    return RawPost(
        source="linkedin",
        external_id=external_id,
        author_name="Fake Author",
        author_url="https://linkedin.com/in/fake",
        content=f"Mission freelance Python. TJM 650€. [{external_id}]",
        post_url=f"https://linkedin.com/posts/{external_id}",
        published_at=_NOW,
        scraped_at=_NOW,
    )


def _make_use_case(
    scraper: FakeScraperGateway | None = None,
) -> tuple[CollectRawPosts, FakeScraperGateway]:
    scraper = scraper or FakeScraperGateway()
    return CollectRawPosts(scraper), scraper


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_collect_raw_posts_returns_list_of_raw_posts() -> None:
    uc, _ = _make_use_case()

    result = await uc.execute(CollectPostsCommand(query="python freelance", limit=10))

    assert isinstance(result, list)
    assert all(isinstance(p, RawPost) for p in result)


async def test_collect_raw_posts_returns_correct_count() -> None:
    posts = [_make_raw_post(f"fake-{i:03d}") for i in range(5)]
    uc, _ = _make_use_case(FakeScraperGateway(posts=posts))

    result = await uc.execute(CollectPostsCommand(query="python", limit=3))

    assert len(result) == 3


async def test_collect_raw_posts_calls_gateway_with_correct_params() -> None:
    uc, scraper = _make_use_case()

    await uc.execute(CollectPostsCommand(query="symfony freelance", limit=5))

    assert scraper.calls == [("symfony freelance", 5)]


async def test_collect_raw_posts_delegates_entirely_to_gateway() -> None:
    """Le use case n'applique aucune logique — il délègue au gateway."""
    uc, scraper = _make_use_case()

    await uc.execute(CollectPostsCommand(query="tech lead", limit=10))

    assert len(scraper.calls) == 1


async def test_collect_raw_posts_returns_empty_list_when_gateway_returns_nothing() -> None:
    uc, _ = _make_use_case(FakeScraperGateway(posts=[]))

    result = await uc.execute(CollectPostsCommand(query="java", limit=10))

    assert result == []
