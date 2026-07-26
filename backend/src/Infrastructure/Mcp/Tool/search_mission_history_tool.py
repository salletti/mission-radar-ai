from typing import Any, Optional

from src.Application.DTO.search_mission_history_query import SearchMissionHistoryQuery
from src.Application.UseCase.search_mission_history import SearchMissionHistory
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class SearchMissionHistoryTool:
    """MCP Tool for search_mission_history — pure read, no business logic. Never talks
    to a Repository directly — only to IdentityResolver and the (new) SearchMissionHistory
    use case. Builds a SearchMissionHistoryQuery from its own explicit parameters, so
    future search criteria only extend this mapping, never the REST-facing
    GetMissionHistory contract."""

    def __init__(self, identity_resolver: IdentityResolver, search_mission_history: SearchMissionHistory) -> None:
        self._identity_resolver = identity_resolver
        self._search_mission_history = search_mission_history

    async def execute(
        self,
        keyword: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        results = await self._search_mission_history.execute(
            SearchMissionHistoryQuery(
                user_profile_id=user_profile_id,
                keyword=keyword,
                min_score=min_score,
                limit=limit,
                offset=offset,
            )
        )
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
                for m in results
            ]
        }
