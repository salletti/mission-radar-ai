from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class SentMissionRepository(ABC):
    """Domain interface for SentMission persistence. Implemented in Infrastructure/."""

    @abstractmethod
    async def find_sent_analyzed_post_ids(self, user_id: UUID) -> set[UUID]: ...

    @abstractmethod
    async def save_many(self, user_id: UUID, analyzed_post_ids: list[UUID], sent_at: datetime) -> None: ...
