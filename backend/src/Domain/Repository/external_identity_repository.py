from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.Domain.Entity.external_identity import ExternalIdentity


class ExternalIdentityRepository(ABC):
    """Domain interface for ExternalIdentity persistence. Implemented in Infrastructure/."""

    @abstractmethod
    async def get_by_provider_and_subject(self, provider: str, subject: str) -> Optional[ExternalIdentity]: ...

    @abstractmethod
    async def save(self, identity: ExternalIdentity) -> None: ...

    @abstractmethod
    async def list_for_user(self, user_profile_id: UUID) -> list[ExternalIdentity]: ...
