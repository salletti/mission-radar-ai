from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.Domain.Entity.analyzed_post import AnalyzedPost


class AnalyzedPostRepository(ABC):
    """Domain interface for AnalyzedPost persistence. Implemented in Infrastructure/."""

    @abstractmethod
    async def save(self, analyzed_post: AnalyzedPost) -> None: ...

    @abstractmethod
    async def get_by_id(self, post_id: UUID) -> Optional[AnalyzedPost]: ...

    @abstractmethod
    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[AnalyzedPost]: ...

    @abstractmethod
    async def list_today_missions(self) -> list[AnalyzedPost]: ...

    @abstractmethod
    async def list_missions(self, limit: int) -> list[AnalyzedPost]: ...

    @abstractmethod
    async def find_by_raw_post_ids(
        self, raw_post_ids: list[UUID]
    ) -> list[AnalyzedPost]: ...

    @abstractmethod
    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]: ...
