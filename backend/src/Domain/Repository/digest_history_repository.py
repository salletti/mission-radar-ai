from abc import ABC, abstractmethod
from uuid import UUID

from src.Domain.Entity.digest_history import DigestHistory


class DigestHistoryRepository(ABC):
    """Abstract repository for DigestHistory. Implemented in Infrastructure/."""

    @abstractmethod
    async def save(self, history: DigestHistory) -> None: ...

    @abstractmethod
    async def find_by_user(self, user_id: UUID) -> list[DigestHistory]: ...
