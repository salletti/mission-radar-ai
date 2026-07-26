from abc import ABC, abstractmethod
from uuid import UUID


class IdentityResolver(ABC):
    """Resolves the business identity (user_profile_id) claimed by the current
    MCP transport session. Pure extraction, no I/O, no business logic. Implemented
    in Infrastructure/Mcp/Identity/."""

    @abstractmethod
    async def resolve(self) -> UUID: ...
