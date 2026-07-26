"""Unit tests for LookupUserByEmail use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.DTO.lookup_user_by_email_query import LookupUserByEmailQuery
from src.Application.UseCase.lookup_user_by_email import LookupUserByEmail
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _make_profile(email: str = "ada@example.com") -> UserProfile:
    return UserProfile(
        id=uuid4(),
        email=email,
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


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, existing: Optional[UserProfile] = None) -> None:
        self._existing = existing

    async def save(self, profile: UserProfile) -> None:
        pass

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

    async def delete(self, profile_id: UUID) -> None:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_found_returns_exists_true() -> None:
    profile = _make_profile("ada@example.com")
    use_case = LookupUserByEmail(repository=FakeUserProfileRepository(existing=profile))

    result = await use_case.execute(LookupUserByEmailQuery(email="ada@example.com"))

    assert result.exists is True
    assert result.user_id == str(profile.id)


@pytest.mark.asyncio
async def test_email_not_found_returns_exists_false() -> None:
    use_case = LookupUserByEmail(repository=FakeUserProfileRepository(existing=None))

    result = await use_case.execute(LookupUserByEmailQuery(email="unknown@example.com"))

    assert result.exists is False
    assert result.user_id is None


@pytest.mark.asyncio
async def test_email_uppercase_is_normalized() -> None:
    profile = _make_profile("ada@example.com")
    use_case = LookupUserByEmail(repository=FakeUserProfileRepository(existing=profile))

    result = await use_case.execute(LookupUserByEmailQuery(email="ADA@EXAMPLE.COM"))

    assert result.exists is True
    assert result.user_id == str(profile.id)


@pytest.mark.asyncio
async def test_email_mixed_case_normalized() -> None:
    profile = _make_profile("ada@example.com")
    use_case = LookupUserByEmail(repository=FakeUserProfileRepository(existing=profile))

    result = await use_case.execute(LookupUserByEmailQuery(email="Ada@Example.Com"))

    assert result.exists is True


@pytest.mark.asyncio
async def test_email_with_whitespace_stripped() -> None:
    profile = _make_profile("ada@example.com")
    use_case = LookupUserByEmail(repository=FakeUserProfileRepository(existing=profile))

    result = await use_case.execute(LookupUserByEmailQuery(email="  ada@example.com  "))

    assert result.exists is True


@pytest.mark.asyncio
async def test_wrong_email_returns_exists_false() -> None:
    profile = _make_profile("ada@example.com")
    use_case = LookupUserByEmail(repository=FakeUserProfileRepository(existing=profile))

    result = await use_case.execute(LookupUserByEmailQuery(email="other@example.com"))

    assert result.exists is False
    assert result.user_id is None
