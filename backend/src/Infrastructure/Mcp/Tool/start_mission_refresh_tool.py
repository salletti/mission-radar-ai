from typing import Any

from src.Application.UseCase.start_mission_refresh import StartMissionRefresh
from src.Domain.ValueObject.pipeline_enums import PipelineTrigger
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver


class StartMissionRefreshTool:
    """MCP Tool for start_mission_refresh — pure orchestration, no business logic. Never
    talks to a Repository directly — only to IdentityResolver and the (existing)
    StartMissionRefresh use case, which already enforces the anti-duplicate-run guard
    and dispatches the worker task. Always triggers with PipelineTrigger.USER, matching
    the REST endpoint's semantics — this Tool is the conversational equivalent of the
    "Refresh" button in the Dashboard, not a new trigger kind."""

    def __init__(self, identity_resolver: IdentityResolver, start_mission_refresh: StartMissionRefresh) -> None:
        self._identity_resolver = identity_resolver
        self._start_mission_refresh = start_mission_refresh

    async def execute(self) -> dict[str, Any]:
        user_profile_id = await self._identity_resolver.resolve()
        run = await self._start_mission_refresh.execute(user_profile_id, PipelineTrigger.USER)
        return {
            "id": str(run.id),
            "user_id": str(run.user_id),
            "pipeline_type": run.pipeline_type.value,
            "trigger_type": run.trigger_type.value,
            "status": run.status.value,
            "current_step": run.current_step.value,
            "progress": run.progress,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error_message": run.error_message,
            "step_outcomes": {step.value: outcome.value for step, outcome in run.step_outcomes.items()},
        }
