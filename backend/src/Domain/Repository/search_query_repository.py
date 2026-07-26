from abc import ABC, abstractmethod
from uuid import UUID

from src.Domain.Entity.search_query import SearchQuery


class SearchQueryRepository(ABC):
    """Domain interface for SearchQuery persistence. Implemented in Infrastructure/."""

    @abstractmethod
    async def save_many(self, queries: list[SearchQuery]) -> None: ...

    @abstractmethod
    async def delete_by_profile(self, user_profile_id: UUID) -> None: ...

    @abstractmethod
    async def get_by_profile(self, user_profile_id: UUID) -> list[SearchQuery]: ...

    @abstractmethod
    async def get_by_source(self, source: str) -> list[SearchQuery]: ...
