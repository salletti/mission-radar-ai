"""Unit tests for GetUserProfile use case — no I/O, no DB."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.Exception.application_error import UserProfileNotFoundError
from src.Application.UseCase.get_user_profile import GetUserProfile
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, existing: Optional[UserProfile] = None) -> None:
        self._existing = existing

    async def save(self, profile: UserProfile) -> None: ...
    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        if self._existing and self._existing.id == profile_id:
            return self._existing
        return None

    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        if self._existing and self._existing.email == email:
            return self._existing
        return None

    async def get_active_profile(self) -> Optional[UserProfile]:
        return self._existing

    async def delete(self, profile_id: UUID) -> None: ...


def _make_profile() -> UserProfile:
    return UserProfile(
        id=uuid4(),
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


@pytest.mark.asyncio
async def test_returns_flattened_dto_for_existing_profile() -> None:
    profile = _make_profile()
    use_case = GetUserProfile(user_profile_repository=FakeUserProfileRepository(existing=profile))

    result = await use_case.execute(profile.id)

    assert result.id == profile.id
    assert result.email == "ada@example.com"
    assert result.full_name == "Ada Lovelace"
    assert result.title == "Senior Python Engineer"
    assert result.years_experience == 10
    assert result.preferred_contract_type == "freelance"
    assert result.target_tjm == 700.0
    assert result.preferred_remote_mode == "full_remote"
    assert result.skills == ("fastapi", "python")
    assert result.availability == _AVAILABILITY
    assert result.location == "Paris"


@pytest.mark.asyncio
async def test_raises_when_profile_not_found() -> None:
    use_case = GetUserProfile(user_profile_repository=FakeUserProfileRepository(existing=None))

    with pytest.raises(UserProfileNotFoundError):
        await use_case.execute(uuid4())
