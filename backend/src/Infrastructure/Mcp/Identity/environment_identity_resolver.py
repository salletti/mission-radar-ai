from uuid import UUID

from src.Infrastructure.Mcp.Identity.exceptions import (
    InvalidIdentityConfigurationError,
    MissingIdentityConfigurationError,
)
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class EnvironmentIdentityResolver(IdentityResolver):
    """Reads the identity claimed for this local, single-user MCP setup from
    MISSION_RADAR_PROFILE_ID. Pure configuration read — no repository access,
    mirroring how a future JwtIdentityResolver would extract the user_profile_id
    already carried in a verified JWT's `sub` claim, without touching the DB either."""

    def __init__(self, profile_id: str) -> None:
        self._profile_id = profile_id

    async def   resolve(self) -> UUID:
        raw = (self._profile_id or "").strip()
        if not raw:
            raise MissingIdentityConfigurationError(
                "MISSION_RADAR_PROFILE_ID is not set — cannot resolve the current MCP identity"
            )
        try:
            return UUID(raw)
        except ValueError as exc:
            raise InvalidIdentityConfigurationError(
                f"MISSION_RADAR_PROFILE_ID is not a valid UUID: {raw!r}"
            ) from exc
