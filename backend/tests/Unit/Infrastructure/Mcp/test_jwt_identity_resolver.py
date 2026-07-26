"""Unit tests for JwtIdentityResolver — fakes only, no DB, no HTTP server."""
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from uuid import UUID, uuid4

import pytest

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.UseCase.resolve_identity import ResolveIdentity
from src.Domain.Entity.external_identity import ExternalIdentity
from src.Domain.Repository.external_identity_repository import ExternalIdentityRepository
from src.Infrastructure.Mcp.Identity.exceptions import (
    InvalidIdentityConfigurationError,
    MissingIdentityConfigurationError,
)
from src.Infrastructure.Mcp.Identity.jwt_identity_resolver import JwtIdentityResolver
from src.Infrastructure.Mcp.Transport.jwt_auth_middleware import _authenticated_identity_ctx

_IDENTITY = AuthenticatedIdentity(provider="auth0", subject="auth0|123", email="ada@example.com")
_PROFILE_ID = uuid4()


class FakeExternalIdentityRepository(ExternalIdentityRepository):
    def __init__(self, existing: Optional[ExternalIdentity] = None) -> None:
        self._existing = existing

    async def get_by_provider_and_subject(self, provider: str, subject: str) -> Optional[ExternalIdentity]:
        if self._existing and self._existing.provider == provider and self._existing.subject == subject:
            return self._existing
        return None

    async def save(self, identity: ExternalIdentity) -> None: ...
    async def list_for_user(self, user_profile_id: UUID) -> list[ExternalIdentity]:
        return []


def _make_context_factory(repo: ExternalIdentityRepository):
    @asynccontextmanager
    async def _factory() -> AsyncIterator[ResolveIdentity]:
        yield ResolveIdentity(external_identity_repository=repo)

    return _factory


@pytest.mark.asyncio
async def test_resolve_returns_linked_user_profile_id() -> None:
    repo = FakeExternalIdentityRepository(
        existing=ExternalIdentity(user_profile_id=_PROFILE_ID, provider="auth0", subject="auth0|123")
    )
    resolver = JwtIdentityResolver(resolve_identity_context_factory=_make_context_factory(repo))

    token = _authenticated_identity_ctx.set(_IDENTITY)
    try:
        result = await resolver.resolve()
    finally:
        _authenticated_identity_ctx.reset(token)

    assert result == _PROFILE_ID


@pytest.mark.asyncio
async def test_resolve_raises_when_no_identity_in_context() -> None:
    repo = FakeExternalIdentityRepository()
    resolver = JwtIdentityResolver(resolve_identity_context_factory=_make_context_factory(repo))

    with pytest.raises(MissingIdentityConfigurationError):
        await resolver.resolve()


@pytest.mark.asyncio
async def test_resolve_raises_when_identity_not_linked() -> None:
    repo = FakeExternalIdentityRepository(existing=None)
    resolver = JwtIdentityResolver(resolve_identity_context_factory=_make_context_factory(repo))

    token = _authenticated_identity_ctx.set(_IDENTITY)
    try:
        with pytest.raises(InvalidIdentityConfigurationError):
            await resolver.resolve()
    finally:
        _authenticated_identity_ctx.reset(token)
