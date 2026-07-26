from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable
from uuid import UUID

from src.Application.Exception.application_error import UserProfileNotLinkedError
from src.Application.UseCase.resolve_identity import ResolveIdentity
from src.Infrastructure.Config.database import AsyncSessionLocal
from src.Infrastructure.Mcp.Identity.exceptions import (
    InvalidIdentityConfigurationError,
    MissingIdentityConfigurationError,
)
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Transport.jwt_auth_middleware import get_authenticated_identity_from_context
from src.Infrastructure.Persistence.Repository.external_identity_repository import (
    SqlAlchemyExternalIdentityRepository,
)


@asynccontextmanager
async def _default_resolve_identity_context() -> AsyncIterator[ResolveIdentity]:
    async with AsyncSessionLocal() as session:
        yield ResolveIdentity(external_identity_repository=SqlAlchemyExternalIdentityRepository(session))


class JwtIdentityResolver(IdentityResolver):
    """Reads the AuthenticatedIdentity that JwtAuthMiddleware already verified for
    this HTTP request and resolves it to a user_profile_id.

    resolve_identity_context_factory defaults to opening its own short-lived
    AsyncSession — matching the per-call session pattern every other MCP
    Tool/Resource in this module already uses — but is injectable so unit tests
    can supply a fake ResolveIdentity without touching the database.
    """

    def __init__(
        self,
        resolve_identity_context_factory: Callable[[], "AsyncIterator[ResolveIdentity]"] = _default_resolve_identity_context,
    ) -> None:
        self._resolve_identity_context_factory = resolve_identity_context_factory

    async def resolve(self) -> UUID:
        identity = get_authenticated_identity_from_context()
        if identity is None:
            raise MissingIdentityConfigurationError(
                "No authenticated identity in context — JwtAuthMiddleware must run first"
            )

        async with self._resolve_identity_context_factory() as resolve_identity:
            try:
                return await resolve_identity.execute(identity)
            except UserProfileNotLinkedError as exc:
                raise InvalidIdentityConfigurationError(str(exc)) from exc
