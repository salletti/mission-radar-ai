from typing import Any

from src.Application.Exception.application_error import UserProfileNotFoundError
from src.Application.UseCase.get_user_profile import GetUserProfile
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class WhoAmITool:
    """MCP validation tool: proves Tool -> IdentityResolver -> Application -> Repository
    wiring end-to-end. Never talks to a Repository directly — only to IdentityResolver
    and the (existing) GetUserProfile use case."""

    def __init__(self, identity_resolver: IdentityResolver, get_user_profile: GetUserProfile) -> None:
        self._identity_resolver = identity_resolver
        self._get_user_profile = get_user_profile

    async def execute(self) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        try:
            profile = await self._get_user_profile.execute(user_profile_id)
        except UserProfileNotFoundError:
            return {"user_id": str(user_profile_id), "exists": False, "email": None}
        return {"user_id": str(user_profile_id), "exists": True, "email": profile.email}
