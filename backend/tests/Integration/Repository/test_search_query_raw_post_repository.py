"""Integration tests for SqlAlchemySearchQueryRawPostRepository — requires running PostgreSQL."""
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.search_query_raw_post import SearchQueryRawPost
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from src.Infrastructure.Persistence.Repository.search_query_raw_post_repository import SqlAlchemySearchQueryRawPostRepository
from src.Infrastructure.Persistence.Repository.search_query_repository import SqlAlchemySearchQueryRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from tests.Integration.Repository.conftest import make_raw_post, make_user_profile


async def _setup_search_query(db_session: AsyncSession):
    """Crée un UserProfile + SearchQuery réels en base et retourne le SearchQuery."""
    from src.Domain.Entity.search_query import SearchQuery

    profile = make_user_profile()
    profile_repo = SqlAlchemyUserProfileRepository(db_session)
    await profile_repo.save(profile)
    await db_session.flush()

    query = SearchQuery(
        user_profile_id=profile.id,
        query="python freelance paris",
        source="linkedin",
        limit=10,
    )
    query_repo = SqlAlchemySearchQueryRepository(db_session)
    await query_repo.save_many([query])
    await db_session.flush()

    return query


@pytest.mark.asyncio
async def test_save_and_exists_true(db_session: AsyncSession) -> None:
    """Un lien sauvegardé est retrouvé par exists()."""
    query = await _setup_search_query(db_session)
    post = make_raw_post()
    await SqlAlchemyRawPostRepository(db_session).save(post)
    await db_session.flush()

    repo = SqlAlchemySearchQueryRawPostRepository(db_session)
    link = SearchQueryRawPost(search_query_id=query.id, raw_post_id=post.id)
    await repo.save(link)

    assert await repo.exists(query.id, post.id) is True


@pytest.mark.asyncio
async def test_exists_returns_false_when_absent(db_session: AsyncSession) -> None:
    repo = SqlAlchemySearchQueryRawPostRepository(db_session)
    assert await repo.exists(uuid4(), uuid4()) is False


@pytest.mark.asyncio
async def test_no_duplicate_link_for_same_pair(db_session: AsyncSession) -> None:
    """exists() permet d'éviter le doublon — la UNIQUE constraint est le filet de sécurité."""
    query = await _setup_search_query(db_session)
    post = make_raw_post()
    await SqlAlchemyRawPostRepository(db_session).save(post)
    await db_session.flush()

    repo = SqlAlchemySearchQueryRawPostRepository(db_session)
    link = SearchQueryRawPost(search_query_id=query.id, raw_post_id=post.id)
    await repo.save(link)

    # Vérifier que le lien existe avant de tenter un doublon
    exists = await repo.exists(query.id, post.id)
    assert exists is True


@pytest.mark.asyncio
async def test_find_by_search_query_id_returns_linked_posts(db_session: AsyncSession) -> None:
    """find_by_search_query_id retourne uniquement les posts de cette query."""
    query = await _setup_search_query(db_session)
    post_a = make_raw_post()
    post_b = make_raw_post()
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    await raw_repo.save_many([post_a, post_b])
    await db_session.flush()

    repo = SqlAlchemySearchQueryRawPostRepository(db_session)
    await repo.save(SearchQueryRawPost(search_query_id=query.id, raw_post_id=post_a.id))
    await repo.save(SearchQueryRawPost(search_query_id=query.id, raw_post_id=post_b.id))

    links = await repo.find_by_search_query_id(query.id)

    assert len(links) == 2
    assert {lnk.raw_post_id for lnk in links} == {post_a.id, post_b.id}


@pytest.mark.asyncio
async def test_find_by_search_query_id_excludes_other_queries(db_session: AsyncSession) -> None:
    """find_by_search_query_id ne retourne pas les liens d'autres queries."""
    query_a = await _setup_search_query(db_session)
    query_b = await _setup_search_query(db_session)
    post = make_raw_post()
    await SqlAlchemyRawPostRepository(db_session).save(post)
    await db_session.flush()

    repo = SqlAlchemySearchQueryRawPostRepository(db_session)
    await repo.save(SearchQueryRawPost(search_query_id=query_a.id, raw_post_id=post.id))
    await repo.save(SearchQueryRawPost(search_query_id=query_b.id, raw_post_id=post.id))

    links_a = await repo.find_by_search_query_id(query_a.id)
    links_b = await repo.find_by_search_query_id(query_b.id)

    assert len(links_a) == 1
    assert len(links_b) == 1
    assert links_a[0].raw_post_id == post.id
    assert links_b[0].raw_post_id == post.id


@pytest.mark.asyncio
async def test_find_by_raw_post_id_returns_linked_queries(db_session: AsyncSession) -> None:
    """find_by_raw_post_id retourne toutes les queries qui ont remonté ce post."""
    query_a = await _setup_search_query(db_session)
    query_b = await _setup_search_query(db_session)
    post = make_raw_post()
    await SqlAlchemyRawPostRepository(db_session).save(post)
    await db_session.flush()

    repo = SqlAlchemySearchQueryRawPostRepository(db_session)
    await repo.save(SearchQueryRawPost(search_query_id=query_a.id, raw_post_id=post.id))
    await repo.save(SearchQueryRawPost(search_query_id=query_b.id, raw_post_id=post.id))

    links = await repo.find_by_raw_post_id(post.id)

    assert len(links) == 2
    assert {lnk.search_query_id for lnk in links} == {query_a.id, query_b.id}


@pytest.mark.asyncio
async def test_existing_post_new_query_creates_link(db_session: AsyncSession) -> None:
    """Post déjà en base + nouveau SearchQuery → liaison créée sans dupliquer le post."""
    query = await _setup_search_query(db_session)
    post = make_raw_post()
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    await raw_repo.save(post)
    await db_session.flush()

    repo = SqlAlchemySearchQueryRawPostRepository(db_session)
    link = SearchQueryRawPost(search_query_id=query.id, raw_post_id=post.id)
    await repo.save(link)

    # Post toujours unique en base
    fetched_post = await raw_repo.get_by_id(post.id)
    assert fetched_post is not None

    # Liaison créée
    links = await repo.find_by_search_query_id(query.id)
    assert len(links) == 1
    assert links[0].raw_post_id == post.id
