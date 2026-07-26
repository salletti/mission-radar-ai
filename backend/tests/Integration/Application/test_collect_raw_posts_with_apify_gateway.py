"""
Tests d'intégration — Phase 3.0.4 : End-to-End Scraping Flow (Mock)

Flux validé :
    CollectPostsCommand
        ↓
    CollectRawPosts
        ↓
    ScraperGateway (ABC)
        ↓
    ApifyScraperGateway
        ↓
    MockApifyProvider
        ↓
    fixtures JSON
        ↓
    RawPost

Instanciation manuelle — aucune DI FastAPI, aucune factory, aucune base de données.
"""

import pytest

from src.Application.DTO.collect_posts_command import CollectPostsCommand
from src.Application.UseCase.collect_raw_posts import CollectRawPosts
from src.Domain.Entity.raw_post import RawPost
from src.Infrastructure.External.Apify.apify_scraper_gateway import ApifyScraperGateway
from src.Infrastructure.External.Apify.mock_apify_provider import MockApifyProvider


@pytest.fixture()
def use_case() -> CollectRawPosts:
    provider = MockApifyProvider()
    gateway = ApifyScraperGateway(provider=provider)
    return CollectRawPosts(scraper=gateway)


@pytest.mark.asyncio
async def test_symfony_query_returns_raw_posts(use_case: CollectRawPosts) -> None:
    command = CollectPostsCommand(query="symfony freelance paris", limit=10)

    posts = await use_case.execute(command)

    assert len(posts) == 10
    assert all(isinstance(p, RawPost) for p in posts)

    first = posts[0]
    assert first.source == "linkedin"
    assert first.external_id == "7468927165061971968"
    assert first.content.strip() != ""
    assert first.author_name == "Delphine Girard"
    assert first.published_at is not None
    assert first.published_at.tzinfo is not None
    assert first.published_at.year == 2026
    assert first.published_at.month == 6
    assert first.published_at.day == 6


@pytest.mark.asyncio
async def test_python_query_returns_raw_posts(use_case: CollectRawPosts) -> None:
    command = CollectPostsCommand(query="python freelance paris", limit=10)

    posts = await use_case.execute(command)

    assert len(posts) == 10
    assert all(isinstance(p, RawPost) for p in posts)

    first = posts[0]
    assert first.source == "linkedin"
    assert first.external_id == "7471260034488832000"
    assert first.content.strip() != ""
    assert first.author_name == "David Roux"
    assert first.published_at is not None
    assert first.published_at.tzinfo is not None


@pytest.mark.asyncio
async def test_unknown_query_returns_empty_list(use_case: CollectRawPosts) -> None:
    command = CollectPostsCommand(query="cobol freelance paris", limit=10)

    posts = await use_case.execute(command)

    assert posts == []


@pytest.mark.asyncio
async def test_limit_is_respected(use_case: CollectRawPosts) -> None:
    command = CollectPostsCommand(query="symfony freelance paris", limit=3)

    posts = await use_case.execute(command)

    assert len(posts) == 3
    assert posts[0].external_id == "7468927165061971968"
