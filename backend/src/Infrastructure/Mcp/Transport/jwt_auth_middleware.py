import contextvars
from typing import Optional

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.Gateway.token_verifier_gateway import TokenVerifierGateway
from src.Infrastructure.External.Auth0.exceptions import TokenVerificationError

# Set by JwtAuthMiddleware before delegating to the app, read by JwtIdentityResolver.
# A plain ContextVar rather than Starlette's Request.state: it only relies on
# asyncio's per-task propagation guarantee, not on how FastMCP threads the ASGI
# scope through its own internal request handling.
_authenticated_identity_ctx: contextvars.ContextVar[Optional[AuthenticatedIdentity]] = contextvars.ContextVar(
    "mcp_authenticated_identity", default=None
)


def get_authenticated_identity_from_context() -> Optional[AuthenticatedIdentity]:
    return _authenticated_identity_ctx.get()


class JwtAuthMiddleware:
    """Verifies the Authorization: Bearer token in front of the MCP HTTP mount —
    replaces SharedSecretMiddleware (Phase 10.2). Fuses "am I allowed to be here"
    with "who am I": verification happens exactly once, here, before any JSON-RPC
    dispatch; JwtIdentityResolver only ever re-reads what this middleware already
    verified. Rejects with a real HTTP 401 + WWW-Authenticate challenge pointing
    at the Protected Resource Metadata endpoint (MCP Authorization spec)."""

    def __init__(
        self,
        app: ASGIApp,
        token_verifier: TokenVerifierGateway,
        expected_audience: str,
        resource_metadata_url: str,
    ) -> None:
        self._app = app
        self._token_verifier = token_verifier
        self._expected_audience = expected_audience
        self._resource_metadata_url = resource_metadata_url

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        auth_header = headers.get(b"authorization", b"").decode("latin-1")
        token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""

        if not token:
            await self._reject(scope, receive, send)
            return

        try:
            identity = await self._token_verifier.verify(token, expected_audience=self._expected_audience)
        except TokenVerificationError:
            await self._reject(scope, receive, send)
            return

        reset_token = _authenticated_identity_ctx.set(identity)
        try:
            await self._app(scope, receive, send)
        finally:
            _authenticated_identity_ctx.reset(reset_token)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        challenge = f'Bearer resource_metadata="{self._resource_metadata_url}"'
        response = PlainTextResponse(
            "Unauthorized", status_code=401, headers={"WWW-Authenticate": challenge}
        )
        await response(scope, receive, send)
