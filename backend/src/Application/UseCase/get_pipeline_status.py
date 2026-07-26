from uuid import UUID

from src.Application.DTO.pipeline_run import PipelineRun
from src.Domain.Repository.pipeline_run_repository import PipelineRunRepository


class GetPipelineStatus:
    """Reads the latest pipeline run for a user — no run yet is a legitimate
    state (None), not an error."""

    def __init__(self, pipeline_run_repository: PipelineRunRepository) -> None:
        self._pipeline_run_repository = pipeline_run_repository

    async def execute(self, user_profile_id: UUID) -> PipelineRun | None:
        run = await self._pipeline_run_repository.find_latest_for_user(user_profile_id)
        if run is None:
            return None

        return PipelineRun(
            id=run.id,
            status=run.status.value,
            current_step=run.current_step.value,
            progress=run.progress,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error_message=run.error_message,
            step_outcomes={step.value: outcome.value for step, outcome in run.step_outcomes.items()},
        )
