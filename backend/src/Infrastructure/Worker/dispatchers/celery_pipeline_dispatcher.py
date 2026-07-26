from uuid import UUID

from src.Application.Gateway.pipeline_dispatcher_gateway import PipelineDispatcherGateway


class CeleryPipelineDispatcher(PipelineDispatcherGateway):
    """Dispatches pipeline tasks via Celery. Lazy import avoids circular dependency with celery_app."""

    def run_mission_refresh(self, pipeline_run_id: UUID, user_id: UUID) -> None:
        from src.Infrastructure.Worker.tasks.run_mission_refresh_task import run_mission_refresh

        run_mission_refresh.delay(str(pipeline_run_id), str(user_id))
