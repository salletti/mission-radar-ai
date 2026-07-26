"""Unit tests for SaveRawPosts use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.UseCase.save_raw_posts import SaveRawPosts
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Entity.search_query_raw_post import SearchQueryRawPost
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.Repository.search_query_raw_post_repository import SearchQueryRawPostRepository

_NOW = datetime(2026, 6, 15, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fake implementations
# ---------------------------------------------------------------------------


class FakeRawPostRepository(RawPostRepository):
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], RawPost] = {}
        self.saved_calls: list[RawPost] = []
        self.save_many_calls: list[list[RawPost]] = []

    async def save(self, raw_post: RawPost) -> None:
        self._store[(raw_post.source, raw_post.external_id)] = raw_post
        self.saved_calls.append(raw_post)

    async def save_many(self, posts: list[RawPost]) -> None:
        self.save_many_calls.append(posts)
        for post in posts:
            self._store[(post.source, post.external_id)] = post

    async def exists_by_external_id(self, source: str, external_id: str) -> bool:
        return (source, external_id) in self._store

    async def get_by_id(self, raw_post_id: UUID) -> Optional[RawPost]:
        for post in self._store.values():
            if post.id == raw_post_id:
                return post
        return None

    async def get_by_source_and_external_id(self, source: str, external_id: str) -> Optional[RawPost]:
        return self._store.get((source, external_id))

    async def list_recent(self, limit: int) -> list[RawPost]:
        return list(self._store.values())[:limit]

    async def find_by_ids(self, ids: list[UUID]) -> list[RawPost]:
        return [p for p in self._store.values() if p.id in ids]


class FakeSearchQueryRawPostRepository(SearchQueryRawPostRepository):
    def __init__(self) -> None:
        self._links: set[tuple[UUID, UUID]] = set()
        self.saved: list[SearchQueryRawPost] = []

    async def save(self, link: SearchQueryRawPost) -> None:
        self._links.add((link.search_query_id, link.raw_post_id))
        self.saved.append(link)

    async def exists(self, search_query_id: UUID, raw_post_id: UUID) -> bool:
        return (search_query_id, raw_post_id) in self._links

    async def find_by_search_query_id(self, search_query_id: UUID) -> list[SearchQueryRawPost]:
        return [lnk for lnk in self.saved if lnk.search_query_id == search_query_id]

    async def find_by_raw_post_id(self, raw_post_id: UUID) -> list[SearchQueryRawPost]:
        return [lnk for lnk in self.saved if lnk.raw_post_id == raw_post_id]

    async def find_by_search_query_ids(self, search_query_ids: list[UUID]) -> list[SearchQueryRawPost]:
        ids = set(search_query_ids)
        return [lnk for lnk in self.saved if lnk.search_query_id in ids]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_post(external_id: str = "ext-001", source: str = "linkedin") -> RawPost:
    return RawPost(
        id=uuid4(),
        source=source,
        external_id=external_id,
        author_name="Author Test",
        author_url="https://linkedin.com/in/test",
        content=f"Mission Python freelance remote. [{external_id}]",
        post_url=f"https://linkedin.com/posts/{external_id}",
        published_at=_NOW,
        scraped_at=_NOW,
    )


def _make_use_case(
    raw_repo: FakeRawPostRepository | None = None,
    link_repo: FakeSearchQueryRawPostRepository | None = None,
) -> tuple[SaveRawPosts, FakeRawPostRepository, FakeSearchQueryRawPostRepository]:
    raw_repo = raw_repo or FakeRawPostRepository()
    link_repo = link_repo or FakeSearchQueryRawPostRepository()
    return SaveRawPosts(raw_repo, link_repo), raw_repo, link_repo


# ---------------------------------------------------------------------------
# Tests — sauvegarde des RawPost
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_empty_list_returns_zero_counts() -> None:
    uc, _, _ = _make_use_case()
    result = await uc.execute([], uuid4())
    assert result.total == 0
    assert result.saved == 0
    assert result.skipped == 0
    assert result.links_created == 0
    assert result.new_post_ids == ()
    assert result.all_post_ids == ()


@pytest.mark.asyncio
async def test_execute_single_new_post_saves_it() -> None:
    uc, repo, _ = _make_use_case()
    post = _make_post("ext-001")

    result = await uc.execute([post], uuid4())

    assert result.total == 1
    assert result.saved == 1
    assert result.skipped == 0
    assert len(repo.save_many_calls) == 1
    assert repo.save_many_calls[0] == [post]
    assert result.new_post_ids == (post.id,)


@pytest.mark.asyncio
async def test_execute_multiple_new_posts_saves_all() -> None:
    uc, repo, _ = _make_use_case()
    posts = [_make_post(f"ext-{i:03d}") for i in range(5)]

    result = await uc.execute(posts, uuid4())

    assert result.total == 5
    assert result.saved == 5
    assert result.skipped == 0
    assert len(result.new_post_ids) == 5
    assert set(result.new_post_ids) == {p.id for p in posts}


@pytest.mark.asyncio
async def test_execute_already_existing_post_is_skipped() -> None:
    raw_repo = FakeRawPostRepository()
    existing = _make_post("ext-001")
    await raw_repo.save(existing)

    uc, _, _ = _make_use_case(raw_repo=raw_repo)
    result = await uc.execute([existing], uuid4())

    assert result.total == 1
    assert result.saved == 0
    assert result.skipped == 1
    assert raw_repo.save_many_calls == [[]]
    assert result.new_post_ids == ()


@pytest.mark.asyncio
async def test_execute_mix_new_and_duplicate_saves_only_new() -> None:
    raw_repo = FakeRawPostRepository()
    existing = _make_post("ext-001")
    await raw_repo.save(existing)

    new_post = _make_post("ext-002")
    uc, _, _ = _make_use_case(raw_repo=raw_repo)
    result = await uc.execute([existing, new_post], uuid4())

    assert result.total == 2
    assert result.saved == 1
    assert result.skipped == 1
    assert raw_repo.save_many_calls[-1] == [new_post]
    assert result.new_post_ids == (new_post.id,)


@pytest.mark.asyncio
async def test_execute_deduplicates_by_source_and_external_id() -> None:
    """Même external_id sur deux sources différentes → deux posts distincts."""
    raw_repo = FakeRawPostRepository()
    linkedin_post = _make_post("ext-001", source="linkedin")
    await raw_repo.save(linkedin_post)

    twitter_post = _make_post("ext-001", source="twitter")
    uc, _, _ = _make_use_case(raw_repo=raw_repo)
    result = await uc.execute([twitter_post], uuid4())

    assert result.saved == 1
    assert result.skipped == 0
    assert result.new_post_ids == (twitter_post.id,)


@pytest.mark.asyncio
async def test_execute_calls_save_many_once_with_all_new_posts() -> None:
    """save_many doit être appelé une seule fois avec la liste complète."""
    uc, repo, _ = _make_use_case()
    posts = [_make_post(f"ext-{i:03d}") for i in range(3)]

    result = await uc.execute(posts, uuid4())

    assert len(repo.save_many_calls) == 1
    assert len(repo.save_many_calls[0]) == 3
    assert len(result.new_post_ids) == 3


# ---------------------------------------------------------------------------
# Tests — all_post_ids
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_post_ids_contains_new_posts() -> None:
    uc, _, _ = _make_use_case()
    posts = [_make_post(f"ext-{i:03d}") for i in range(3)]

    result = await uc.execute(posts, uuid4())

    assert set(result.all_post_ids) == {p.id for p in posts}
    assert result.all_post_ids == result.new_post_ids


@pytest.mark.asyncio
async def test_all_post_ids_contains_existing_post_with_db_id() -> None:
    """Pour un post déjà en base, all_post_ids doit contenir l'ID DB (pas l'ID du domain entity entrant)."""
    raw_repo = FakeRawPostRepository()
    db_post = _make_post("ext-001")
    await raw_repo.save(db_post)

    incoming_post = _make_post("ext-001")
    assert incoming_post.id != db_post.id

    uc, _, _ = _make_use_case(raw_repo=raw_repo)
    result = await uc.execute([incoming_post], uuid4())

    assert result.skipped == 1
    assert result.new_post_ids == ()
    assert db_post.id in result.all_post_ids
    assert incoming_post.id not in result.all_post_ids


@pytest.mark.asyncio
async def test_all_post_ids_is_union_of_new_and_existing() -> None:
    """all_post_ids = new_post_ids ∪ existing_post_ids."""
    raw_repo = FakeRawPostRepository()
    existing = _make_post("ext-001")
    await raw_repo.save(existing)

    new_post = _make_post("ext-002")
    uc, _, _ = _make_use_case(raw_repo=raw_repo)
    result = await uc.execute([existing, new_post], uuid4())

    assert len(result.all_post_ids) == 2
    assert existing.id in result.all_post_ids
    assert new_post.id in result.all_post_ids
    assert set(result.new_post_ids) == {new_post.id}


# ---------------------------------------------------------------------------
# Tests — création des liaisons SearchQuery → RawPost
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_links_created_for_all_new_posts() -> None:
    uc, _, link_repo = _make_use_case()
    query_id = uuid4()
    posts = [_make_post(f"ext-{i:03d}") for i in range(3)]

    result = await uc.execute(posts, query_id)

    assert result.links_created == 3
    assert len(link_repo.saved) == 3
    linked_post_ids = {lnk.raw_post_id for lnk in link_repo.saved}
    assert linked_post_ids == {p.id for p in posts}


@pytest.mark.asyncio
async def test_link_created_for_existing_post_if_not_yet_linked() -> None:
    """Un post dupliqué (déjà en raw_posts) doit quand même être lié à la SearchQuery."""
    raw_repo = FakeRawPostRepository()
    db_post = _make_post("ext-001")
    await raw_repo.save(db_post)

    uc, _, link_repo = _make_use_case(raw_repo=raw_repo)
    query_id = uuid4()
    result = await uc.execute([_make_post("ext-001")], query_id)

    assert result.skipped == 1
    assert result.links_created == 1
    assert link_repo.saved[0].raw_post_id == db_post.id
    assert link_repo.saved[0].search_query_id == query_id


@pytest.mark.asyncio
async def test_link_not_duplicated_if_already_exists() -> None:
    """Idempotence : si la liaison existe déjà, elle n'est pas re-créée."""
    uc, _, link_repo = _make_use_case()
    query_id = uuid4()
    post = _make_post("ext-001")

    await uc.execute([post], query_id)
    result = await uc.execute([post], query_id)

    assert result.links_created == 0
    assert len(link_repo.saved) == 1


@pytest.mark.asyncio
async def test_same_post_linked_to_different_queries() -> None:
    """Le même post peut être lié à plusieurs SearchQuery."""
    raw_repo = FakeRawPostRepository()
    link_repo = FakeSearchQueryRawPostRepository()
    uc = SaveRawPosts(raw_repo, link_repo)

    post = _make_post("ext-001")
    query_id_1 = uuid4()
    query_id_2 = uuid4()

    await uc.execute([post], query_id_1)
    result = await uc.execute([_make_post("ext-001")], query_id_2)

    assert result.links_created == 1
    assert len(link_repo.saved) == 2
    queries = {lnk.search_query_id for lnk in link_repo.saved}
    assert queries == {query_id_1, query_id_2}


@pytest.mark.asyncio
async def test_links_have_correct_search_query_id() -> None:
    uc, _, link_repo = _make_use_case()
    query_id = uuid4()
    posts = [_make_post(f"ext-{i:03d}") for i in range(2)]

    await uc.execute(posts, query_id)

    for link in link_repo.saved:
        assert link.search_query_id == query_id
