from typing import Any
from uuid import UUID

from src.Application.DTO.get_mission_details_query import GetMissionDetailsQuery
from src.Application.UseCase.get_mission_details import GetMissionDetails
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class ExplainMissionMatchTool:
    """MCP Tool for explain_mission_match — pure read, no business logic. Never talks
    to a Repository directly — only to IdentityResolver and the (existing)
    GetMissionDetails use case, which already verifies mission ownership against the
    resolved user_profile_id. Response is limited to the computed explanation
    (score breakdown, matching reasons, matched/missing skills) — it deliberately
    omits the original post content, already covered by the missions Resource."""

    def __init__(self, identity_resolver: IdentityResolver, get_mission_details: GetMissionDetails) -> None:
        self._identity_resolver = identity_resolver
        self._get_mission_details = get_mission_details

    async def execute(self, mission_match_id: UUID) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        detail = await self._get_mission_details.execute(
            GetMissionDetailsQuery(mission_match_id=mission_match_id, user_profile_id=user_profile_id)
        )
        explanation = detail.explanation

        return {
            "mission_match_id": str(detail.mission_match_id),
            "title": detail.title,
            "company": detail.company,
            "global_score": detail.global_score,
            "score_details": detail.score_details,
            "score_breakdown": {
                "skills": explanation.score_breakdown.skills,
                "experience": explanation.score_breakdown.experience,
                "location": explanation.score_breakdown.location,
                "contract": explanation.score_breakdown.contract,
                "daily_rate": explanation.score_breakdown.daily_rate,
            },
            "matching_reasons": list(explanation.matching_reasons),
            "matched_skills": list(detail.matched_skills),
            "missing_skills": list(detail.missing_skills),
            "warnings": list(explanation.warnings),
            "recommendations": list(explanation.recommendations),
        }
