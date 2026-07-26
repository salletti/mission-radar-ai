import asyncio

import jwt
from jwt import PyJWKClient

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.Gateway.token_verifier_gateway import TokenVerifierGateway
from src.Infrastructure.External.Auth0.exceptions import TokenVerificationError

# Namespaced custom claim added by the Auth0 Action configured in Phase 10.4.1
# — Auth0 access tokens carry no profile info by default, only the ID token
# does, and the backend only ever sees the access token.
_EMAIL_CLAIM = "https://mission-radar.dev/email"


class Auth0TokenVerifierGateway(TokenVerifierGateway):
    """Verifies Auth0-issued RS256 JWTs against the tenant's JWKS. The only
    place in the codebase that knows the "auth0" provider name or the
    namespaced email claim — everything downstream (ResolveIdentity, etc.)
    only ever sees the provider-agnostic AuthenticatedIdentity."""

    def __init__(self, domain: str) -> None:
        self._issuer = f"https://{domain}/"
        self._jwks_client = PyJWKClient(f"https://{domain}/.well-known/jwks.json", cache_keys=True)

    async def verify(self, token: str, expected_audience: str) -> AuthenticatedIdentity:
        try:
            signing_key = await asyncio.to_thread(self._jwks_client.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=expected_audience,
                issuer=self._issuer,
            )
        except jwt.PyJWTError as exc:
            raise TokenVerificationError(str(exc)) from exc

        return AuthenticatedIdentity(
            provider="auth0",
            subject=claims["sub"],
            email=claims.get(_EMAIL_CLAIM),
            claims=claims,
        )
