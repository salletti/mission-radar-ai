from abc import ABC, abstractmethod
from uuid import UUID

from src.Domain.Entity.search_query_raw_post import SearchQueryRawPost


class SearchQueryRawPostRepository(ABC):
    """Domain interface for SearchQueryRawPost persistence. Implemented in Infrastructure/."""

    @abstractmethod
    async def save(self, link: SearchQueryRawPost) -> None: ...

    @abstractmethod
    async def exists(self, search_query_id: UUID, raw_post_id: UUID) -> bool: ...

    @abstractmethod
    async def find_by_search_query_id(self, search_query_id: UUID) -> list[SearchQueryRawPost]: ...

    @abstractmethod
    async def find_by_raw_post_id(self, raw_post_id: UUID) -> list[SearchQueryRawPost]: ...

    @abstractmethod
    async def find_by_search_query_ids(
        self, search_query_ids: list[UUID]
    ) -> list[SearchQueryRawPost]: ...
