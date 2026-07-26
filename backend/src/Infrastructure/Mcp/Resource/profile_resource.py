from typing import Any

from src.Application.UseCase.get_user_profile import GetUserProfile
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class ProfileResource:
    """MCP Resource for mission-radar://profile — pure read, no business logic.
    Never talks to a Repository directly — only to IdentityResolver and the
    (existing) GetUserProfile use case."""

    def __init__(self, identity_resolver: IdentityResolver, get_user_profile: GetUserProfile) -> None:
        self._identity_resolver = identity_resolver
        self._get_user_profile = get_user_profile

    async def execute(self) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        profile = await self._get_user_profile.execute(user_profile_id)
        return {
            "id": str(profile.id),
            "email": profile.email,
            "full_name": profile.full_name,
            "title": profile.title,
            "years_experience": profile.years_experience,
            "preferred_contract_type": profile.preferred_contract_type,
            "target_tjm": profile.target_tjm,
            "preferred_remote_mode": profile.preferred_remote_mode,
            "skills": list(profile.skills),
            "availability": profile.availability.isoformat(),
            "location": profile.location,
        }
