from starlette.applications import Starlette
from starlette.middleware import Middleware

from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Auth0.auth0_token_verifier_gateway import Auth0TokenVerifierGateway
from src.Infrastructure.Mcp.Factory.factory import build_mcp_server
from src.Infrastructure.Mcp.Identity.jwt_identity_resolver import JwtIdentityResolver
from src.Infrastructure.Mcp.Transport.jwt_auth_middleware import JwtAuthMiddleware


def build_mcp_http_app() -> Starlette:
    """Builds the MCP server as a mountable ASGI app, gated by JwtAuthMiddleware
    (Phase 10.4.5 — replaces the temporary SharedSecretMiddleware from Phase 10.2).

    Passes a JwtIdentityResolver-based factory to build_mcp_server() instead of
    its default EnvironmentIdentityResolver — real authentication only applies to
    this HTTP-mounted server, the stdio pilot (server.py) is unaffected. The
    returned app exposes its own `.lifespan`, which the caller MUST pass to
    FastAPI(lifespan=...) when mounting, otherwise the MCP session manager never
    starts.
    """
    token_verifier = Auth0TokenVerifierGateway(domain=settings.AUTH0_DOMAIN)

    mcp = build_mcp_server(identity_resolver_factory=JwtIdentityResolver)
    return mcp.http_app(
        path="/",
        middleware=[
            Middleware(
                JwtAuthMiddleware,
                token_verifier=token_verifier,
                expected_audience=settings.AUTH0_MCP_AUDIENCE,
                resource_metadata_url=settings.MCP_PROTECTED_RESOURCE_METADATA_URL,
            )
        ],
    )
