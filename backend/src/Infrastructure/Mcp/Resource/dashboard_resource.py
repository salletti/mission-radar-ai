from typing import Any

from src.Application.UseCase.get_dashboard_summary import GetDashboardSummary
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class DashboardResource:
    """MCP Resource for mission-radar://dashboard — pure read, no business logic.
    Never talks to a Repository directly — only to IdentityResolver and the
    (existing) GetDashboardSummary use case."""

    def __init__(self, identity_resolver: IdentityResolver, get_dashboard_summary: GetDashboardSummary) -> None:
        self._identity_resolver = identity_resolver
        self._get_dashboard_summary = get_dashboard_summary

    async def execute(self) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        summary = await self._get_dashboard_summary.execute(user_profile_id)
        return {
            "kpis": {
                "total_missions": summary.kpis.total_missions,
                "new_today": summary.kpis.new_today,
                "average_score": summary.kpis.average_score,
                "last_refresh": summary.kpis.last_refresh.isoformat() if summary.kpis.last_refresh else None,
                "pipeline_status": summary.kpis.pipeline_status,
            },
            "health": {
                "status": summary.health.status,
                "last_pipeline_duration_seconds": summary.health.last_pipeline_duration_seconds,
            },
        }
