from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.Domain.Entity.search_query import SearchQuery
from src.Domain.Exception.domain_exceptions import InvalidSearchQueryError
from src.Domain.Repository.search_query_repository import SearchQueryRepository


@dataclass(frozen=True)
class UpdateSearchQueriesCommand:
    profile_id: UUID
    queries: list[str]


class UpdateSearchQueries:
    """Replace all search queries for a profile with a user-edited list.

    ≈ Application Service : orchestre SearchQueryRepository (DELETE + INSERT).
    Appelé après l'étape de review des queries dans l'onboarding.
    """

    def __init__(self, search_query_repo: SearchQueryRepository) -> None:
        self._repo = search_query_repo

    async def execute(self, command: UpdateSearchQueriesCommand) -> int:
        new_queries: list[SearchQuery] = []
        for raw in command.queries:
            query_str = raw.strip()
            if not query_str:
                continue
            try:
                new_queries.append(
                    SearchQuery(
                        user_profile_id=command.profile_id,
                        query=query_str,
                        source="linkedin",
                        limit=50,
                    )
                )
            except InvalidSearchQueryError:
                pass

        await self._repo.delete_by_profile(command.profile_id)
        await self._repo.save_many(new_queries)
        return len(new_queries)
