from uuid import UUID, uuid4

from src.Application.Exception.application_error import PipelineAlreadyRunningError, UserProfileNotFoundError
from src.Application.Gateway.pipeline_dispatcher_gateway import PipelineDispatcherGateway
from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.Repository.pipeline_run_repository import PipelineRunRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.ValueObject.pipeline_enums import PipelineStatus, PipelineStep, PipelineType, PipelineTrigger


class StartMissionRefresh:
    """Creates a PipelineRun and dispatches the mission refresh worker task.

    Validates that the user exists and that no pipeline is already running
    before creating a new PENDING run and triggering the async worker.
    """

    def __init__(
        self,
        pipeline_run_repo: PipelineRunRepository,
        user_profile_repo: UserProfileRepository,
        dispatcher: PipelineDispatcherGateway,
    ) -> None:
        self._pipeline_run_repo = pipeline_run_repo
        self._user_profile_repo = user_profile_repo
        self._dispatcher = dispatcher

    async def execute(self, user_id: UUID, trigger: PipelineTrigger) -> PipelineRun:
        profile = await self._user_profile_repo.get_by_id(user_id)
        if profile is None:
            raise UserProfileNotFoundError(f"UserProfile {user_id} not found")

        running = await self._pipeline_run_repo.find_running_for_user(user_id)
        if running is not None:
            raise PipelineAlreadyRunningError(
                f"Pipeline {running.id} is already running for user {user_id}"
            )

        run = PipelineRun(
            id=uuid4(),
            user_id=user_id,
            pipeline_type=PipelineType.MISSION_REFRESH,
            trigger_type=trigger,
            status=PipelineStatus.PENDING,
            current_step=PipelineStep.COLLECT,
            progress=0.0,
        )

        await self._pipeline_run_repo.save(run)
        self._dispatcher.run_mission_refresh(run.id, user_id)

        return run
