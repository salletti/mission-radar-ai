from typing import Any

from src.Application.UseCase.get_pipeline_status import GetPipelineStatus
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class PipelineResource:
    """MCP Resource for mission-radar://pipeline — pure read, no business logic.
    Never talks to a Repository directly — only to IdentityResolver and the
    (new) GetPipelineStatus use case. Stays strictly factual: no run yet is
    expressed as {"last_run": None}, never interpreted (e.g. "never_run")."""

    def __init__(self, identity_resolver: IdentityResolver, get_pipeline_status: GetPipelineStatus) -> None:
        self._identity_resolver = identity_resolver
        self._get_pipeline_status = get_pipeline_status

    async def execute(self) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        run = await self._get_pipeline_status.execute(user_profile_id)
        if run is None:
            return {"last_run": None}

        return {
            "last_run": {
                "id": str(run.id),
                "status": run.status,
                "current_step": run.current_step,
                "progress": run.progress,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "error_message": run.error_message,
                "step_outcomes": run.step_outcomes,
            }
        }
