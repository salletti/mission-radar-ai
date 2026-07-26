import asyncio
import logging

from src.Application.Exception.application_error import PipelineAlreadyRunningError
from src.Application.UseCase.start_mission_refresh import StartMissionRefresh
from src.Domain.ValueObject.pipeline_enums import PipelineTrigger
from src.Infrastructure.Config.database import CeleryAsyncSessionLocal as AsyncSessionLocal
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository
from src.Infrastructure.Persistence.Repository.search_query_repository import SqlAlchemySearchQueryRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from src.Infrastructure.Worker.dispatchers.celery_pipeline_dispatcher import CeleryPipelineDispatcher

logger = logging.getLogger(__name__)


async def _fetch_and_dispatch() -> None:
    async with AsyncSessionLocal() as session:
        repo = SqlAlchemySearchQueryRepository(session)
        queries = await repo.get_by_source("linkedin")

    if not queries:
        logger.warning("dispatch_collection: no active search queries — skipping")
        return

    user_ids = {q.user_profile_id for q in queries}
    logger.info("dispatch_collection: found %d users with active queries", len(user_ids))

    for user_id in user_ids:
        async with AsyncSessionLocal() as session:
            use_case = StartMissionRefresh(
                pipeline_run_repo=SqlAlchemyPipelineRunRepository(session),
                user_profile_repo=SqlAlchemyUserProfileRepository(session),
                dispatcher=CeleryPipelineDispatcher(),
            )
            try:
                run = await use_case.execute(user_id, PipelineTrigger.SCHEDULER)
                await session.commit()
                logger.info(
                    "dispatch_collection: started pipeline_run=%s for user=%s",
                    run.id,
                    user_id,
                )
            except PipelineAlreadyRunningError:
                logger.info(
                    "dispatch_collection: pipeline already running for user=%s — skipping",
                    user_id,
                )


def dispatch_collection() -> None:
    """Appelée directement par DynamicCollectionScheduler dans le processus Beat — aucun hop RabbitMQ."""
    asyncio.run(_fetch_and_dispatch())
