"""Unit tests for UpdateSearchQueriesTool — no I/O, no DB, no real MCP server. Fakes only."""
from uuid import UUID, uuid4

import pytest

from src.Application.UseCase.update_search_queries import UpdateSearchQueries
from src.Domain.Entity.search_query import SearchQuery
from src.Domain.Repository.search_query_repository import SearchQueryRepository
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Tool.update_search_queries_tool import UpdateSearchQueriesTool


class FakeSearchQueryRepository(SearchQueryRepository):
    def __init__(self) -> None:
        self._queries: list[SearchQuery] = []
        self.deleted_for: list[UUID] = []

    async def save_many(self, queries: list[SearchQuery]) -> None:
        self._queries.extend(queries)

    async def delete_by_profile(self, user_profile_id: UUID) -> None:
        self.deleted_for.append(user_profile_id)
        self._queries = [q for q in self._queries if q.user_profile_id != user_profile_id]

    async def get_by_profile(self, user_profile_id: UUID) -> list[SearchQuery]:
        return [q for q in self._queries if q.user_profile_id == user_profile_id]

    async def get_by_source(self, source: str) -> list[SearchQuery]:
        return [q for q in self._queries if q.source == source]


class FakeIdentityResolver(IdentityResolver):
    def __init__(self, user_profile_id: UUID) -> None:
        self._user_profile_id = user_profile_id

    async def resolve(self) -> UUID:
        return self._user_profile_id


def _make_tool(user_id: UUID, repo: FakeSearchQueryRepository) -> UpdateSearchQueriesTool:
    update_search_queries = UpdateSearchQueries(search_query_repo=repo)
    return UpdateSearchQueriesTool(
        identity_resolver=FakeIdentityResolver(user_id), update_search_queries=update_search_queries
    )


@pytest.mark.asyncio
async def test_update_search_queries_saves_new_list_and_returns_count() -> None:
    user_id = uuid4()
    repo = FakeSearchQueryRepository()
    tool = _make_tool(user_id, repo)

    payload = await tool.execute(["python freelance paris", "kubernetes freelance remote"])

    assert payload == {"count": 2}
    saved = await repo.get_by_profile(user_id)
    assert {q.query for q in saved} == {"python freelance paris", "kubernetes freelance remote"}


@pytest.mark.asyncio
async def test_update_search_queries_replaces_previous_queries() -> None:
    user_id = uuid4()
    repo = FakeSearchQueryRepository()
    await repo.save_many([SearchQuery(user_profile_id=user_id, query="old query", source="linkedin", limit=50)])

    tool = _make_tool(user_id, repo)
    payload = await tool.execute(["new query"])

    assert payload == {"count": 1}
    saved = await repo.get_by_profile(user_id)
    assert [q.query for q in saved] == ["new query"]


@pytest.mark.asyncio
async def test_update_search_queries_drops_blank_entries() -> None:
    user_id = uuid4()
    repo = FakeSearchQueryRepository()
    tool = _make_tool(user_id, repo)

    payload = await tool.execute(["python freelance", "  ", ""])

    assert payload == {"count": 1}


@pytest.mark.asyncio
async def test_update_search_queries_only_affects_current_user() -> None:
    user_a = uuid4()
    user_b = uuid4()
    repo = FakeSearchQueryRepository()
    await repo.save_many([SearchQuery(user_profile_id=user_b, query="other user query", source="linkedin", limit=50)])

    tool = _make_tool(user_a, repo)
    await tool.execute(["python freelance"])

    assert len(await repo.get_by_profile(user_b)) == 1
    assert len(await repo.get_by_profile(user_a)) == 1
