from typing import Any

from src.Application.UseCase.send_digest_now import SendDigestNow
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class SendDigestNowTool:
    """MCP Tool for send_digest_now — pure orchestration, no business logic. Never
    talks to a Repository or Gateway directly — only to IdentityResolver and the
    (existing) SendDigestNow use case."""

    def __init__(self, identity_resolver: IdentityResolver, send_digest_now: SendDigestNow) -> None:
        self._identity_resolver = identity_resolver
        self._send_digest_now = send_digest_now

    async def execute(self) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        result = await self._send_digest_now.execute(user_profile_id)
        return {
            "status": result.status,
            "missions_count": result.missions_count,
            "provider_message_id": result.provider_message_id,
            "error_message": result.error_message,
        }
