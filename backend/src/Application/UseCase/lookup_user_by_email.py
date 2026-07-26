from src.Application.DTO.lookup_user_by_email_query import LookupUserByEmailQuery
from src.Application.DTO.lookup_user_by_email_result import LookupUserByEmailResult
from src.Domain.Repository.user_profile_repository import UserProfileRepository


class LookupUserByEmail:
    """Find a user profile by email — returns exists + user_id, never raises."""

    def __init__(self, repository: UserProfileRepository) -> None:
        self._repository = repository

    async def execute(self, query: LookupUserByEmailQuery) -> LookupUserByEmailResult:
        profile = await self._repository.get_by_email(query.email.strip().lower())
        if profile is None:
            return LookupUserByEmailResult(exists=False, user_id=None)
        return LookupUserByEmailResult(exists=True, user_id=str(profile.id))
