"""Unit tests for ResolveIdentity — no I/O, no DB, fakes only."""
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.Exception.application_error import UserProfileNotLinkedError
from src.Application.UseCase.resolve_identity import ResolveIdentity
from src.Domain.Entity.external_identity import ExternalIdentity
from src.Domain.Repository.external_identity_repository import ExternalIdentityRepository

_PROFILE_ID = uuid4()


class FakeExternalIdentityRepository(ExternalIdentityRepository):
    def __init__(self, existing: Optional[ExternalIdentity] = None) -> None:
        self._existing = existing
        self.saved: list[ExternalIdentity] = []

    async def get_by_provider_and_subject(self, provider: str, subject: str) -> Optional[ExternalIdentity]:
        if self._existing and self._existing.provider == provider and self._existing.subject == subject:
            return self._existing
        return None

    async def save(self, identity: ExternalIdentity) -> None:
        self.saved.append(identity)

    async def list_for_user(self, user_profile_id: UUID) -> list[ExternalIdentity]:
        return [i for i in self.saved if i.user_profile_id == user_profile_id]


async def test_execute_returns_linked_user_profile_id() -> None:
    repo = FakeExternalIdentityRepository(
        existing=ExternalIdentity(user_profile_id=_PROFILE_ID, provider="auth0", subject="auth0|123")
    )
    use_case = ResolveIdentity(external_identity_repository=repo)

    result = await use_case.execute(AuthenticatedIdentity(provider="auth0", subject="auth0|123"))

    assert result == _PROFILE_ID


async def test_execute_raises_when_not_linked() -> None:
    repo = FakeExternalIdentityRepository()
    use_case = ResolveIdentity(external_identity_repository=repo)

    with pytest.raises(UserProfileNotLinkedError):
        await use_case.execute(AuthenticatedIdentity(provider="auth0", subject="auth0|unknown"))


async def test_execute_does_not_match_across_different_providers() -> None:
    repo = FakeExternalIdentityRepository(
        existing=ExternalIdentity(user_profile_id=_PROFILE_ID, provider="auth0", subject="same-subject")
    )
    use_case = ResolveIdentity(external_identity_repository=repo)

    with pytest.raises(UserProfileNotLinkedError):
        await use_case.execute(AuthenticatedIdentity(provider="some-other-provider", subject="same-subject"))


async def test_execute_never_hardcodes_a_provider_name() -> None:
    """ResolveIdentity must read provider from the DTO, never from a literal —
    verified here by using a provider name that isn't "auth0" at all."""
    repo = FakeExternalIdentityRepository(
        existing=ExternalIdentity(user_profile_id=_PROFILE_ID, provider="keycloak", subject="kc|123")
    )
    use_case = ResolveIdentity(external_identity_repository=repo)

    result = await use_case.execute(AuthenticatedIdentity(provider="keycloak", subject="kc|123"))

    assert result == _PROFILE_ID
