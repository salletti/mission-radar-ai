from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.Domain.Entity.mission_match import MissionMatch


class MissionMatchRepository(ABC):
    """Domain interface for MissionMatch persistence. Implemented in Infrastructure/."""

    @abstractmethod
    async def save(self, match: MissionMatch) -> None: ...

    @abstractmethod
    async def save_many(self, matches: list[MissionMatch]) -> None: ...

    @abstractmethod
    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatch]: ...

    @abstractmethod
    async def get_by_user(self, user_id: UUID) -> list[MissionMatch]: ...

    @abstractmethod
    async def get_by_post(self, post_id: UUID) -> list[MissionMatch]: ...

    @abstractmethod
    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatch]: ...

    @abstractmethod
    async def delete_user_matches(self, user_id: UUID) -> None: ...
