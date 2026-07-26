from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.Application.UseCase.start_mission_refresh import StartMissionRefresh
from src.Infrastructure.Config.database import get_db_session
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from src.Infrastructure.Worker.dispatchers.celery_pipeline_dispatcher import CeleryPipelineDispatcher


async def get_start_mission_refresh(
    db: AsyncSession = Depends(get_db_session),
) -> StartMissionRefresh:
    return StartMissionRefresh(
        pipeline_run_repo=SqlAlchemyPipelineRunRepository(db),
        user_profile_repo=SqlAlchemyUserProfileRepository(db),
        dispatcher=CeleryPipelineDispatcher(),
    )


async def get_pipeline_run_repository(
    db: AsyncSession = Depends(get_db_session),
) -> SqlAlchemyPipelineRunRepository:
    return SqlAlchemyPipelineRunRepository(db)
