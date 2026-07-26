from typing import Any

from src.Application.DTO.get_activity_history_query import GetActivityHistoryQuery
from src.Application.UseCase.get_activity_history import GetActivityHistory
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class ActivityResource:
    """MCP Resource for mission-radar://activity — pure read, no business logic.
    Never talks to a Repository directly — only to IdentityResolver and the
    (existing) GetActivityHistory use case."""

    def __init__(self, identity_resolver: IdentityResolver, get_activity_history: GetActivityHistory) -> None:
        self._identity_resolver = identity_resolver
        self._get_activity_history = get_activity_history

    async def execute(self) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        page = await self._get_activity_history.execute(GetActivityHistoryQuery(user_profile_id=user_profile_id))
        return {
            "items": [
                {
                    "type": event.type,
                    "occurred_at": event.occurred_at.isoformat(),
                    "title": event.title,
                    "description": event.description,
                    "score": event.score,
                    "mission_match_id": str(event.mission_match_id) if event.mission_match_id else None,
                    "digest_history_id": str(event.digest_history_id) if event.digest_history_id else None,
                }
                for event in page.items
            ],
            "total": page.total,
            "limit": page.limit,
            "offset": page.offset,
        }
