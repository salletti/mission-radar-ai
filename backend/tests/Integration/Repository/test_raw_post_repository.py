"""Integration tests for SqlAlchemyRawPostRepository — requires running PostgreSQL."""
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from tests.Integration.Repository.conftest import make_raw_post


@pytest.mark.asyncio
async def test_save_and_get_by_id(db_session: AsyncSession) -> None:
    repo = SqlAlchemyRawPostRepository(db_session)
    post = make_raw_post()

    await repo.save(post)
    fetched = await repo.get_by_id(post.id)

    assert fetched is not None
    assert fetched.id == post.id
    assert fetched.source == post.source
    assert fetched.content == post.content


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_absent(db_session: AsyncSession) -> None:
    repo = SqlAlchemyRawPostRepository(db_session)
    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_exists_by_external_id_true(db_session: AsyncSession) -> None:
    repo = SqlAlchemyRawPostRepository(db_session)
    post = make_raw_post(source="linkedin", external_id="ext-123")
    await repo.save(post)

    exists = await repo.exists_by_external_id("linkedin", "ext-123")
    assert exists is True


@pytest.mark.asyncio
async def test_exists_by_external_id_false(db_session: AsyncSession) -> None:
    repo = SqlAlchemyRawPostRepository(db_session)
    exists = await repo.exists_by_external_id("linkedin", "never-saved")
    assert exists is False


@pytest.mark.asyncio
async def test_exists_by_external_id_different_source(db_session: AsyncSession) -> None:
    repo = SqlAlchemyRawPostRepository(db_session)
    await repo.save(make_raw_post(source="linkedin", external_id="ext-456"))

    # Same external_id but different source → False
    exists = await repo.exists_by_external_id("twitter", "ext-456")
    assert exists is False


@pytest.mark.asyncio
async def test_list_recent_returns_ordered_by_scraped_at(db_session: AsyncSession) -> None:
    from datetime import timedelta
    repo = SqlAlchemyRawPostRepository(db_session)
    from tests.Integration.Repository.conftest import NOW

    older = make_raw_post(scraped_at=NOW - timedelta(hours=2))
    newer = make_raw_post(scraped_at=NOW)
    await repo.save(older)
    await repo.save(newer)

    results = await repo.list_recent(limit=2)
    assert len(results) == 2
    assert results[0].scraped_at >= results[1].scraped_at


@pytest.mark.asyncio
async def test_list_recent_respects_limit(db_session: AsyncSession) -> None:
    repo = SqlAlchemyRawPostRepository(db_session)
    for _ in range(5):
        await repo.save(make_raw_post())

    results = await repo.list_recent(limit=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_save_many_persists_all(db_session: AsyncSession) -> None:
    repo = SqlAlchemyRawPostRepository(db_session)
    posts = [make_raw_post() for _ in range(3)]

    await repo.save_many(posts)

    for post in posts:
        fetched = await repo.get_by_id(post.id)
        assert fetched is not None
        assert fetched.external_id == post.external_id


@pytest.mark.asyncio
async def test_save_many_empty_list_is_noop(db_session: AsyncSession) -> None:
    repo = SqlAlchemyRawPostRepository(db_session)
    # Doit se terminer sans exception — c'est le seul invariant attendu
    await repo.save_many([])
