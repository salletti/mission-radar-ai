"""Unit tests for JwtAuthMiddleware — Starlette TestClient, fake TokenVerifierGateway, no DB."""
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.Gateway.token_verifier_gateway import TokenVerifierGateway
from src.Infrastructure.External.Auth0.exceptions import TokenVerificationError
from src.Infrastructure.Mcp.Transport.jwt_auth_middleware import (
    JwtAuthMiddleware,
    get_authenticated_identity_from_context,
)

_AUDIENCE = "https://api.mission-radar.dev/mcp"
_RESOURCE_METADATA_URL = "http://testserver/.well-known/oauth-protected-resource"


class FakeTokenVerifierGateway(TokenVerifierGateway):
    def __init__(self, valid_token: str = "valid-token") -> None:
        self._valid_token = valid_token

    async def verify(self, token: str, expected_audience: str) -> AuthenticatedIdentity:
        if token != self._valid_token or expected_audience != _AUDIENCE:
            raise TokenVerificationError("invalid token")
        return AuthenticatedIdentity(provider="auth0", subject="auth0|123")


async def _echo_identity(request):
    identity = get_authenticated_identity_from_context()
    return PlainTextResponse(identity.subject if identity else "none")


def _build_app() -> Starlette:
    return Starlette(
        routes=[Route("/", _echo_identity)],
        middleware=[
            Middleware(
                JwtAuthMiddleware,
                token_verifier=FakeTokenVerifierGateway(),
                expected_audience=_AUDIENCE,
                resource_metadata_url=_RESOURCE_METADATA_URL,
            )
        ],
    )


def test_request_without_authorization_header_is_rejected() -> None:
    client = TestClient(_build_app())
    response = client.get("/")
    assert response.status_code == 401


def test_request_without_token_gets_www_authenticate_challenge() -> None:
    client = TestClient(_build_app())
    response = client.get("/")
    assert _RESOURCE_METADATA_URL in response.headers["www-authenticate"]


def test_request_with_invalid_token_is_rejected() -> None:
    client = TestClient(_build_app())
    response = client.get("/", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401


def test_request_with_valid_token_reaches_the_app() -> None:
    client = TestClient(_build_app())
    response = client.get("/", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200


def test_authenticated_identity_available_to_downstream_app() -> None:
    client = TestClient(_build_app())
    response = client.get("/", headers={"Authorization": "Bearer valid-token"})
    assert response.text == "auth0|123"


def test_malformed_authorization_header_is_rejected() -> None:
    client = TestClient(_build_app())
    response = client.get("/", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401
