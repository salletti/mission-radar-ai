from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.Domain.Entity.user_profile import UserProfile


class UserProfileRepository(ABC):
    """Domain interface for UserProfile persistence. Implemented in Infrastructure/."""

    @abstractmethod
    async def save(self, profile: UserProfile) -> None: ...

    @abstractmethod
    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserProfile]: ...

    @abstractmethod
    async def get_active_profile(self) -> Optional[UserProfile]: ...

    @abstractmethod
    async def delete(self, profile_id: UUID) -> None: ...
