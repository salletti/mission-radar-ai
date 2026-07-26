"""Unit tests for ProfileResource — no I/O, no DB, no real MCP server. Fakes only."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.UseCase.get_user_profile import GetUserProfile
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Resource.profile_resource import ProfileResource

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, existing: Optional[UserProfile] = None) -> None:
        self._existing = existing

    async def save(self, profile: UserProfile) -> None: ...
    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        if self._existing and self._existing.id == profile_id:
            return self._existing
        return None

    async def get_by_email(self, email: str) -> Optional[UserProfile]: return None
    async def get_active_profile(self) -> Optional[UserProfile]: return self._existing
    async def delete(self, profile_id: UUID) -> None: ...


class FakeIdentityResolver(IdentityResolver):
    def __init__(self, user_profile_id: UUID) -> None:
        self._user_profile_id = user_profile_id

    async def resolve(self) -> UUID:
        return self._user_profile_id


@pytest.mark.asyncio
async def test_profile_resource_returns_structured_profile() -> None:
    profile_id = uuid4()
    profile = UserProfile(
        id=profile_id,
        email="ada@example.com",
        full_name="Ada Lovelace",
        title="Senior Python Engineer",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack(("python", "fastapi")),
        availability=_AVAILABILITY,
        location="Paris",
    )
    get_user_profile = GetUserProfile(user_profile_repository=FakeUserProfileRepository(existing=profile))
    resource = ProfileResource(
        identity_resolver=FakeIdentityResolver(profile_id), get_user_profile=get_user_profile
    )

    payload = await resource.execute()

    assert payload == {
        "id": str(profile_id),
        "email": "ada@example.com",
        "full_name": "Ada Lovelace",
        "title": "Senior Python Engineer",
        "years_experience": 10,
        "preferred_contract_type": "freelance",
        "target_tjm": 700.0,
        "preferred_remote_mode": "full_remote",
        "skills": ["fastapi", "python"],
        "availability": _AVAILABILITY.isoformat(),
        "location": "Paris",
    }
