from typing import Any

from src.Application.UseCase.update_search_queries import UpdateSearchQueries, UpdateSearchQueriesCommand
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class UpdateSearchQueriesTool:
    """MCP Tool for update_search_queries — pure orchestration, no business logic. Never
    talks to a Repository directly — only to IdentityResolver and the (existing)
    UpdateSearchQueries use case, which replaces the user's full list of search
    queries (DELETE + INSERT) — this Tool does not support adding or removing a
    single query in isolation, the caller must always pass the complete new list."""

    def __init__(self, identity_resolver: IdentityResolver, update_search_queries: UpdateSearchQueries) -> None:
        self._identity_resolver = identity_resolver
        self._update_search_queries = update_search_queries

    async def execute(self, queries: list[str]) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        count = await self._update_search_queries.execute(
            UpdateSearchQueriesCommand(profile_id=user_profile_id, queries=queries)
        )
        return {"count": count}
