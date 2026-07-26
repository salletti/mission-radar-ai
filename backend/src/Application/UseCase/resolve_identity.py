from uuid import UUID

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.Exception.application_error import UserProfileNotLinkedError
from src.Domain.Repository.external_identity_repository import ExternalIdentityRepository


class ResolveIdentity:
    """Resolves an AuthenticatedIdentity to the UserProfile it is linked to.

    provider/subject come from the DTO itself, never from a literal in this
    Use Case — swapping/adding an OIDC provider only requires a new
    TokenVerifierGateway implementation, this class never changes.
    """

    def __init__(self, external_identity_repository: ExternalIdentityRepository) -> None:
        self._external_identity_repository = external_identity_repository

    async def execute(self, identity: AuthenticatedIdentity) -> UUID:
        link = await self._external_identity_repository.get_by_provider_and_subject(
            identity.provider, identity.subject
        )
        if link is None:
            raise UserProfileNotLinkedError(
                f"No UserProfile linked to {identity.provider}:{identity.subject}"
            )
        return link.user_profile_id
