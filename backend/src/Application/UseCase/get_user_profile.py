from uuid import UUID

from src.Application.DTO.user_profile import UserProfile
from src.Application.Exception.application_error import UserProfileNotFoundError
from src.Domain.Repository.user_profile_repository import UserProfileRepository


class GetUserProfile:
    """Reads a single UserProfile by id — the shared identity-to-profile lookup
    reused by WhoAmITool and the profile MCP Resource."""

    def __init__(self, user_profile_repository: UserProfileRepository) -> None:
        self._user_profile_repository = user_profile_repository

    async def execute(self, user_profile_id: UUID) -> UserProfile:
        profile = await self._user_profile_repository.get_by_id(user_profile_id)
        if profile is None:
            raise UserProfileNotFoundError(f"No profile for id {user_profile_id}")

        return UserProfile(
            id=profile.id,
            email=profile.email,
            full_name=profile.full_name,
            title=profile.title,
            years_experience=profile.years_experience,
            preferred_contract_type=profile.preferred_contract_type.value,
            target_tjm=profile.target_tjm,
            preferred_remote_mode=profile.preferred_remote_mode.value,
            skills=profile.skills.technologies,
            availability=profile.availability,
            location=profile.location,
        )
