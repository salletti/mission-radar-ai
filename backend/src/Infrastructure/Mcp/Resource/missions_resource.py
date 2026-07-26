from typing import Any

from src.Application.DTO.get_today_missions_query import GetTodayMissionsQuery
from src.Application.UseCase.get_today_missions import GetTodayMissions
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class MissionsResource:
    """MCP Resource for mission-radar://missions — pure read, no business logic.
    Never talks to a Repository directly — only to IdentityResolver and the
    (existing) GetTodayMissions use case."""

    def __init__(self, identity_resolver: IdentityResolver, get_today_missions: GetTodayMissions) -> None:
        self._identity_resolver = identity_resolver
        self._get_today_missions = get_today_missions

    async def execute(self) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        missions = await self._get_today_missions.execute(GetTodayMissionsQuery(user_profile_id=user_profile_id))
        return {
            "missions": [
                {
                    "mission_match_id": str(m.mission_match_id),
                    "analyzed_post_id": str(m.analyzed_post_id),
                    "raw_post_id": str(m.raw_post_id),
                    "author_name": m.author_name,
                    "content_excerpt": m.content_excerpt,
                    "post_url": m.post_url,
                    "detected_stack": list(m.detected_stack),
                    "detected_contract_type": m.detected_contract_type,
                    "detected_remote_mode": m.detected_remote_mode,
                    "global_score": m.global_score,
                    "score_details": m.score_details,
                    "detected_tjm": m.detected_tjm,
                    "title": m.title,
                    "company": m.company,
                    "location": m.location,
                }
                for m in missions
            ]
        }
