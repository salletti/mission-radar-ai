from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.Domain.Entity.raw_post import RawPost


class RawPostRepository(ABC):
    """Domain interface for RawPost persistence. Implemented in Infrastructure/."""

    @abstractmethod
    async def save(self, raw_post: RawPost) -> None: ...

    @abstractmethod
    async def exists_by_external_id(self, source: str, external_id: str) -> bool: ...

    @abstractmethod
    async def get_by_id(self, raw_post_id: UUID) -> Optional[RawPost]: ...

    @abstractmethod
    async def save_many(self, posts: list[RawPost]) -> None: ...

    @abstractmethod
    async def get_by_source_and_external_id(self, source: str, external_id: str) -> Optional[RawPost]: ...

    @abstractmethod
    async def list_recent(self, limit: int) -> list[RawPost]: ...

    @abstractmethod
    async def find_by_ids(self, ids: list[UUID]) -> list[RawPost]: ...
